#!/usr/bin/env bash
#
# uninstall.sh - Uninstall claude-auto-translate skill from Claude Code
#
# Usage:
#   ./uninstall.sh           # Remove from user directory
#   ./uninstall.sh --project # Also remove from current project
#   ./uninstall.sh --all     # Remove from user AND all project directories
#
# This script:
#   1. Removes the hook entry from Claude Code settings.json
#   2. Removes skill files from ~/.claude/skills/claude-auto-translate/
#   3. Optionally removes from project-level .claude/ as well
#   4. Preserves user config files (with --keep-config) or removes them
#

set -e

SKILL_NAME="claude-auto-translate"

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
UNINSTALL_PROJECT=false
UNINSTALL_ALL=false
KEEP_CONFIG=false

for arg in "$@"; do
    case $arg in
        --project)
            UNINSTALL_PROJECT=true
            ;;
        --all)
            UNINSTALL_ALL=true
            ;;
        --keep-config)
            KEEP_CONFIG=true
            ;;
        --help|-h)
            echo "Usage: $0 [--project] [--all] [--keep-config]"
            echo ""
            echo "Options:"
            echo "  --project      Also remove from current project's .claude/ directory"
            echo "  --all          Remove from user AND project directories"
            echo "  --keep-config  Preserve config.json files (with API keys)"
            echo "  --help         Show this help message"
            exit 0
            ;;
    esac
done

# Paths
USER_SKILLS_DIR="$HOME/.claude/skills/$SKILL_NAME"
USER_SETTINGS="$HOME/.claude/settings.json"
PROJECT_DIR=".claude/$SKILL_NAME"

#
# Remove hook from Claude Code settings.json
#
# Per Claude Code hooks docs, the configuration has THREE levels of nesting:
# 1. Hook event (e.g., "UserPromptSubmit")
# 2. Matcher groups (array of objects with "hooks" arrays)
# 3. Hook handlers (inside each group's "hooks" array)
#
# We remove only our handler, drop empty groups, keep other hooks.
#
unregister_hook() {
    local settings_file="$1"
    
    if [ ! -f "$settings_file" ]; then
        info "Settings file not found: $settings_file"
        return
    fi
    
    # Backup the settings file
    local backup_file="${settings_file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$settings_file" "$backup_file"
    info "Backed up settings to: $backup_file"
    
    # Use Python to safely remove the hook
    python3 << PYTHON_SCRIPT
import json
import sys

settings_file = "$settings_file"
skill_name = "$SKILL_NAME"

try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    print("No valid settings file to modify")
    sys.exit(0)

if 'hooks' not in settings:
    print("No hooks configured")
    sys.exit(0)

modified = False
removed_count = 0

# Check UserPromptSubmit hooks (three-level nesting)
hook_type = 'UserPromptSubmit'
if hook_type in settings['hooks']:
    matcher_groups = settings['hooks'][hook_type]
    
    if isinstance(matcher_groups, list):
        # Iterate through matcher groups
        new_groups = []
        for group in matcher_groups:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            
            handlers = group.get('hooks', [])
            if not isinstance(handlers, list):
                handlers = [handlers] if handlers else []
            
            # Filter out our handlers from this group
            new_handlers = []
            for handler in handlers:
                if isinstance(handler, dict):
                    cmd = handler.get('command', '')
                else:
                    cmd = str(handler)
                
                if skill_name not in cmd:
                    new_handlers.append(handler)
                else:
                    removed_count += 1
                    modified = True
            
            # Keep the group only if it still has handlers
            if new_handlers:
                group['hooks'] = new_handlers
                new_groups.append(group)
            # If group becomes empty, we drop it (don't add to new_groups)
        
        if removed_count > 0:
            print("Removed " + str(removed_count) + " hook(s)")
        
        # Update or remove the hook type
        if new_groups:
            settings['hooks'][hook_type] = new_groups
        else:
            del settings['hooks'][hook_type]

# Clean up empty hooks object
if 'hooks' in settings and not settings['hooks']:
    del settings['hooks']

if modified:
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    print("Updated " + settings_file)
else:
    print("No hooks to remove")
PYTHON_SCRIPT
}

#
# Remove skill files
#
remove_skill_files() {
    local dir="$1"
    
    if [ ! -d "$dir" ]; then
        info "Directory not found: $dir"
        return
    fi
    
    info "Removing skill files from $dir"
    
    # Remove Python files
    rm -f "$dir/hook.py"
    rm -f "$dir/SKILL.md"
    rm -rf "$dir/src"
    
    # Remove config unless --keep-config
    if [ "$KEEP_CONFIG" = false ]; then
        rm -f "$dir/config.json"
    else
        if [ -f "$dir/config.json" ]; then
            info "Keeping config file: $dir/config.json"
        fi
    fi
    
    # Remove directory if empty
    if [ -d "$dir" ] && [ -z "$(ls -A "$dir")" ]; then
        rmdir "$dir"
        info "Removed empty directory: $dir"
    elif [ -d "$dir" ]; then
        info "Directory not empty, keeping: $dir"
    fi
}

#
# Main uninstallation
#

info "Uninstalling $SKILL_NAME..."

# 1. Remove hook from user settings
unregister_hook "$USER_SETTINGS"

# 2. Remove skill files from user directory
remove_skill_files "$USER_SKILLS_DIR"

# Clean up parent directory if empty
PARENT_DIR="$HOME/.claude/skills"
if [ -d "$PARENT_DIR" ] && [ -z "$(ls -A "$PARENT_DIR")" ]; then
    rmdir "$PARENT_DIR"
fi

# 3. Optionally remove from project directory
if [ "$UNINSTALL_PROJECT" = true ] || [ "$UNINSTALL_ALL" = true ]; then
    if [ -d "$PROJECT_DIR" ]; then
        remove_skill_files "$PROJECT_DIR"
        
        # Clean up parent .claude directory if empty
        if [ -d ".claude" ] && [ -z "$(ls -A ".claude")" ]; then
            rmdir ".claude"
        fi
    else
        info "Project directory not found: $PROJECT_DIR"
    fi
fi

echo ""
info "Uninstallation complete!"
echo ""
echo "Restart Claude Code to apply changes."
echo ""

if [ "$KEEP_CONFIG" = true ]; then
    echo "Your config files were preserved. Remove manually if no longer needed."
fi
