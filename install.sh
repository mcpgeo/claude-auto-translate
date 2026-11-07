#!/usr/bin/env bash
#
# install.sh - Install claude-auto-translate skill for Claude Code
#
# Usage:
#   ./install.sh           # Install to user directory (~/.claude/skills/)
#   ./install.sh --project # Also install to current project (.claude/)
#
# This script:
#   1. Copies skill files to ~/.claude/skills/claude-auto-translate/
#   2. Registers the hook in Claude Code settings.json
#   3. Creates an example config file (if none exists)
#   4. Optionally installs to project-level .claude/ as well
#

set -e

SKILL_NAME="claude-auto-translate"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Parse arguments
INSTALL_PROJECT=false
for arg in "$@"; do
    case $arg in
        --project)
            INSTALL_PROJECT=true
            ;;
        --help|-h)
            echo "Usage: $0 [--project]"
            echo ""
            echo "Options:"
            echo "  --project  Also install to current project's .claude/ directory"
            echo "  --help     Show this help message"
            exit 0
            ;;
    esac
done

# Paths
USER_SKILLS_DIR="$HOME/.claude/skills/$SKILL_NAME"
USER_SETTINGS="$HOME/.claude/settings.json"
PROJECT_DIR=".claude/$SKILL_NAME"

# Ensure required directories exist
mkdir -p "$HOME/.claude/skills"
mkdir -p "$(dirname "$USER_SETTINGS")"

#
# Install skill files to user directory
#
install_skill_files() {
    local dest="$1"
    
    info "Installing skill files to $dest"
    
    mkdir -p "$dest"
    mkdir -p "$dest/src"
    
    # Copy Python files
    cp "$SCRIPT_DIR/hook.py" "$dest/"
    cp "$SCRIPT_DIR/src/__init__.py" "$dest/src/"
    cp "$SCRIPT_DIR/src/config.py" "$dest/src/"
    cp "$SCRIPT_DIR/src/detect.py" "$dest/src/"
    cp "$SCRIPT_DIR/src/providers.py" "$dest/src/"
    cp "$SCRIPT_DIR/src/translate.py" "$dest/src/"
    
    # Copy SKILL.md if it exists
    if [ -f "$SCRIPT_DIR/SKILL.md" ]; then
        cp "$SCRIPT_DIR/SKILL.md" "$dest/"
    fi
    
    # Make hook executable
    chmod +x "$dest/hook.py"
    
    info "Skill files installed to $dest"
}

#
# Create example config if needed
#
create_config() {
    local dest="$1"
    local config_file="$dest/config.json"
    local example_file="$SCRIPT_DIR/config.example.json"
    
    if [ -f "$config_file" ]; then
        info "Config file already exists: $config_file"
        return
    fi
    
    if [ -f "$example_file" ]; then
        cp "$example_file" "$config_file"
    else
        # Create minimal config
        cat > "$config_file" << 'EOF'
{
  "enabled": true,
  "user_language": "Georgian",
  "working_language": "English",
  "display_mode": "native",
  "provider": "anthropic",
  "timeout_seconds": 10
}
EOF
    fi
    
    # Secure the config file (it may contain API keys)
    chmod 600 "$config_file"
    
    info "Created config file: $config_file (chmod 600)"
}

#
# Register hook in Claude Code settings.json
#
# Per Claude Code hooks docs, the configuration has THREE levels of nesting:
# 1. Hook event (e.g., "UserPromptSubmit")
# 2. Matcher groups (array of objects, each with optional "matcher" and required "hooks")
# 3. Hook handlers (the "hooks" array inside each matcher group)
#
# Correct structure:
# "UserPromptSubmit": [{"hooks": [{"type":"command","command":"...","timeout":15}]}]
#
# UserPromptSubmit has no matcher support, so we omit the matcher field.
# timeout is in seconds; set to 15s (above the default 10s request timeout)
# Never exit 2 (blocks prompt), so we add || exit 0 failsafe
#
register_hook() {
    local settings_file="$1"
    local hook_path="$2"
    
    # Build the hook command with failsafe (never exit 2)
    local hook_cmd="python3 \"$hook_path\" || exit 0"
    
    # Create settings file if it doesn't exist
    if [ ! -f "$settings_file" ]; then
        echo '{}' > "$settings_file"
    fi
    
    # Backup the settings file
    local backup_file="${settings_file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$settings_file" "$backup_file"
    info "Backed up settings to: $backup_file"
    
    # Use Python to safely merge the hook configuration
    python3 << PYTHON_SCRIPT
import json
import sys

settings_file = "$settings_file"
skill_name = "$SKILL_NAME"
hook_cmd = """$hook_cmd"""

try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    settings = {}

# Ensure hooks structure exists
if 'hooks' not in settings:
    settings['hooks'] = {}

# Define our hook handler per Claude Code settings.json schema
# timeout is in seconds; set to 15s (above the default 10s request timeout)
our_handler = {
    "type": "command",
    "command": hook_cmd,
    "timeout": 15
}

# Get or create the UserPromptSubmit matcher groups array
hook_type = 'UserPromptSubmit'
if hook_type not in settings['hooks']:
    settings['hooks'][hook_type] = []

# Ensure it's a list of matcher groups
matcher_groups = settings['hooks'][hook_type]
if not isinstance(matcher_groups, list):
    matcher_groups = [matcher_groups] if matcher_groups else []
    settings['hooks'][hook_type] = matcher_groups

# Look for our hook in existing matcher groups
# We need to check inside each group's "hooks" array
already_registered = False
for group in matcher_groups:
    if not isinstance(group, dict):
        continue
    
    handlers = group.get('hooks', [])
    if not isinstance(handlers, list):
        handlers = [handlers] if handlers else []
        group['hooks'] = handlers
    
    for i, handler in enumerate(handlers):
        if isinstance(handler, dict):
            cmd = handler.get('command', '')
            if skill_name in cmd:
                # Update existing handler
                handlers[i] = our_handler
                already_registered = True
                print("Updated existing hook for " + skill_name)
                break
    
    if already_registered:
        break

if not already_registered:
    # Add a new matcher group with our handler
    # UserPromptSubmit has no matcher support, so we omit the matcher field
    new_group = {
        "hooks": [our_handler]
    }
    matcher_groups.append(new_group)
    print("Registered new hook for " + skill_name)

# Write back
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("Hook registered in " + settings_file)
PYTHON_SCRIPT
    
    if [ $? -ne 0 ]; then
        error "Failed to register hook in settings"
    fi
    
    info "Hook registered successfully"
}

#
# Main installation
#

info "Installing $SKILL_NAME..."

# 1. Install to user skills directory
install_skill_files "$USER_SKILLS_DIR"
create_config "$USER_SKILLS_DIR"

# 2. Register hook in user settings
register_hook "$USER_SETTINGS" "$USER_SKILLS_DIR/hook.py"

# 3. Optionally install to project directory
if [ "$INSTALL_PROJECT" = true ]; then
    info "Installing to project directory..."
    install_skill_files "$PROJECT_DIR"
    create_config "$PROJECT_DIR"
    
    # Add to .gitignore if not already there
    if [ -f ".gitignore" ]; then
        if ! grep -q "^\.claude/$SKILL_NAME/config\.json$" .gitignore 2>/dev/null; then
            echo "" >> .gitignore
            echo "# claude-auto-translate user config (contains API keys)" >> .gitignore
            echo ".claude/$SKILL_NAME/config.json" >> .gitignore
            info "Added config.json to .gitignore"
        fi
    fi
fi

echo ""
info "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Set your API key:"
echo "     export ANTHROPIC_API_KEY='your-key-here'"
echo "     (or edit ~/.claude/skills/$SKILL_NAME/config.json)"
echo ""
echo "  2. Configure your language in the config file if not Georgian"
echo ""
echo "  3. Restart Claude Code to load the new hook"
echo ""
echo "To disable temporarily:"
echo "     export CLAUDE_AUTO_TRANSLATE_ENABLED=false"
echo ""
