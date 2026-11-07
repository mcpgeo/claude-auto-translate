"""Tests for installer idempotency."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInstallerIdempotency(unittest.TestCase):
    """Test that installer is idempotent."""
    
    @classmethod
    def setUpClass(cls):
        """Find the script directory."""
        cls.script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.install_script = os.path.join(cls.script_dir, "install.sh")
        cls.uninstall_script = os.path.join(cls.script_dir, "uninstall.sh")
    
    def setUp(self):
        """Create a temporary HOME directory for testing."""
        self.temp_home = tempfile.mkdtemp(prefix="claude_test_home_")
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = self.temp_home
        
        # Create minimal directory structure
        os.makedirs(os.path.join(self.temp_home, ".claude"), exist_ok=True)
    
    def tearDown(self):
        """Clean up temporary directory."""
        if self.original_home:
            os.environ["HOME"] = self.original_home
        else:
            del os.environ["HOME"]
        
        shutil.rmtree(self.temp_home, ignore_errors=True)
    
    def test_install_creates_skill_directory(self):
        """Install should create the skill directory."""
        result = subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        skill_dir = os.path.join(
            self.temp_home, ".claude", "skills", "claude-auto-translate"
        )
        
        self.assertTrue(os.path.isdir(skill_dir), f"Skill dir not created. stderr: {result.stderr}")
    
    def test_install_creates_hook_file(self):
        """Install should create the hook.py file."""
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        hook_file = os.path.join(
            self.temp_home, ".claude", "skills", "claude-auto-translate", "hook.py"
        )
        
        self.assertTrue(os.path.isfile(hook_file))
    
    def test_install_creates_settings_with_hook(self):
        """Install should register hook in settings.json with three-level nesting."""
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        settings_file = os.path.join(self.temp_home, ".claude", "settings.json")
        
        self.assertTrue(os.path.isfile(settings_file))
        
        with open(settings_file) as f:
            settings = json.load(f)
        
        self.assertIn("hooks", settings)
        self.assertIn("UserPromptSubmit", settings["hooks"])
        
        # Verify three-level nesting per Claude Code docs
        matcher_groups = settings["hooks"]["UserPromptSubmit"]
        self.assertIsInstance(matcher_groups, list)
        self.assertGreater(len(matcher_groups), 0)
        
        # Each matcher group should have a "hooks" array
        group = matcher_groups[0]
        self.assertIsInstance(group, dict)
        self.assertIn("hooks", group)
        self.assertIsInstance(group["hooks"], list)
    
    def test_install_idempotent_single_hook(self):
        """Running install twice should not duplicate hooks."""
        # Run install twice
        for _ in range(2):
            subprocess.run(
                ["bash", self.install_script],
                cwd=self.script_dir,
                capture_output=True,
                env={**os.environ, "HOME": self.temp_home}
            )
        
        settings_file = os.path.join(self.temp_home, ".claude", "settings.json")
        
        with open(settings_file) as f:
            settings = json.load(f)
        
        matcher_groups = settings["hooks"]["UserPromptSubmit"]
        
        # Count our handlers across all matcher groups
        our_handlers = []
        for group in matcher_groups:
            if isinstance(group, dict) and "hooks" in group:
                for handler in group["hooks"]:
                    if isinstance(handler, dict) and "claude-auto-translate" in handler.get("command", ""):
                        our_handlers.append(handler)
        
        self.assertEqual(len(our_handlers), 1, "Expected 1 hook handler, found {}".format(len(our_handlers)))
    
    def test_install_hook_has_correct_format(self):
        """Hook should have correct three-level nested format per Claude Code docs."""
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        settings_file = os.path.join(self.temp_home, ".claude", "settings.json")
        
        with open(settings_file) as f:
            settings = json.load(f)
        
        # Level 1: hook event
        self.assertIn("UserPromptSubmit", settings["hooks"])
        matcher_groups = settings["hooks"]["UserPromptSubmit"]
        
        # Level 2: matcher groups (array of objects)
        self.assertIsInstance(matcher_groups, list)
        self.assertGreater(len(matcher_groups), 0)
        
        # Find our group and handler
        our_handler = None
        for group in matcher_groups:
            self.assertIsInstance(group, dict)
            # Level 3: hooks array inside each group
            self.assertIn("hooks", group)
            self.assertIsInstance(group["hooks"], list)
            
            for handler in group["hooks"]:
                if isinstance(handler, dict) and "claude-auto-translate" in handler.get("command", ""):
                    our_handler = handler
                    break
        
        self.assertIsNotNone(our_handler, "Our handler not found in nested structure")
        
        # Per Claude Code docs, command hooks need:
        # - type: "command"
        # - command: the command string
        # - timeout: in seconds (not milliseconds)
        self.assertEqual(our_handler.get("type"), "command")
        self.assertIn("command", our_handler)
        self.assertIn("timeout", our_handler)
        
        # Timeout should be in seconds (reasonable value, not milliseconds)
        timeout = our_handler.get("timeout")
        self.assertIsInstance(timeout, (int, float))
        self.assertGreater(timeout, 0)
        self.assertLess(timeout, 100)  # Should be seconds, not milliseconds
    
    def test_install_hook_has_failsafe(self):
        """Hook command should have || exit 0 failsafe to never block."""
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        settings_file = os.path.join(self.temp_home, ".claude", "settings.json")
        
        with open(settings_file) as f:
            settings = json.load(f)
        
        # Find our handler in the nested structure
        matcher_groups = settings["hooks"]["UserPromptSubmit"]
        our_handler = None
        for group in matcher_groups:
            if isinstance(group, dict) and "hooks" in group:
                for handler in group["hooks"]:
                    if isinstance(handler, dict) and "claude-auto-translate" in handler.get("command", ""):
                        our_handler = handler
                        break
        
        self.assertIsNotNone(our_handler)
        
        # Command should end with || exit 0 to never exit 2 (which blocks prompt)
        command = our_handler.get("command", "")
        self.assertIn("|| exit 0", command)
    
    def test_install_preserves_other_hooks(self):
        """Install should not clobber existing hooks in other matcher groups."""
        # Create settings with an existing hook in proper three-level structure
        settings_file = os.path.join(self.temp_home, ".claude", "settings.json")
        existing_settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {"type": "command", "command": "echo 'other hook'", "timeout": 5}
                        ]
                    }
                ]
            }
        }
        with open(settings_file, "w") as f:
            json.dump(existing_settings, f)
        
        # Run install
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        with open(settings_file) as f:
            settings = json.load(f)
        
        matcher_groups = settings["hooks"]["UserPromptSubmit"]
        
        # Should have two matcher groups (one existing, one ours)
        self.assertEqual(len(matcher_groups), 2)
        
        # Collect all handlers
        all_handlers = []
        for group in matcher_groups:
            if isinstance(group, dict) and "hooks" in group:
                all_handlers.extend(group["hooks"])
        
        # Original handler should be preserved
        other_handlers = [
            h for h in all_handlers
            if isinstance(h, dict) and "other hook" in h.get("command", "")
        ]
        self.assertEqual(len(other_handlers), 1)
        
        # Our handler should be added
        our_handlers = [
            h for h in all_handlers
            if isinstance(h, dict) and "claude-auto-translate" in h.get("command", "")
        ]
        self.assertEqual(len(our_handlers), 1)
    
    def test_install_creates_config_with_600_permissions(self):
        """Install should create config.json with chmod 600."""
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        config_file = os.path.join(
            self.temp_home, ".claude", "skills", "claude-auto-translate", "config.json"
        )
        
        self.assertTrue(os.path.isfile(config_file))
        
        # Check permissions (600 = owner read/write only)
        mode = os.stat(config_file).st_mode & 0o777
        self.assertEqual(mode, 0o600)
    
    def test_install_does_not_overwrite_existing_config(self):
        """Install should not overwrite existing config file."""
        # Create skill directory and config first
        skill_dir = os.path.join(
            self.temp_home, ".claude", "skills", "claude-auto-translate"
        )
        os.makedirs(skill_dir, exist_ok=True)
        
        config_file = os.path.join(skill_dir, "config.json")
        custom_config = {"enabled": False, "custom_key": "custom_value"}
        with open(config_file, "w") as f:
            json.dump(custom_config, f)
        
        # Run install
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        # Config should be unchanged
        with open(config_file) as f:
            config = json.load(f)
        
        self.assertEqual(config.get("custom_key"), "custom_value")
    
    def test_uninstall_removes_hook(self):
        """Uninstall should remove hook from settings (three-level structure)."""
        # First install
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        # Then uninstall
        subprocess.run(
            ["bash", self.uninstall_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        settings_file = os.path.join(self.temp_home, ".claude", "settings.json")
        
        with open(settings_file) as f:
            settings = json.load(f)
        
        # Check hooks are removed - collect all handlers from nested structure
        matcher_groups = settings.get("hooks", {}).get("UserPromptSubmit", [])
        our_handlers = []
        for group in matcher_groups:
            if isinstance(group, dict) and "hooks" in group:
                for handler in group["hooks"]:
                    if isinstance(handler, dict) and "claude-auto-translate" in handler.get("command", ""):
                        our_handlers.append(handler)
        
        self.assertEqual(len(our_handlers), 0)
    
    def test_uninstall_preserves_other_hooks(self):
        """Uninstall should not remove other hooks (three-level structure)."""
        # Create settings with our hook and another hook in proper three-level structure
        settings_file = os.path.join(self.temp_home, ".claude", "settings.json")
        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {"type": "command", "command": "echo 'other hook'", "timeout": 5}
                        ]
                    },
                    {
                        "hooks": [
                            {"type": "command", "command": "python3 claude-auto-translate/hook.py", "timeout": 15}
                        ]
                    }
                ]
            }
        }
        with open(settings_file, "w") as f:
            json.dump(settings, f)
        
        # Create skill directory so uninstall has something to remove
        skill_dir = os.path.join(
            self.temp_home, ".claude", "skills", "claude-auto-translate"
        )
        os.makedirs(skill_dir, exist_ok=True)
        
        # Run uninstall
        subprocess.run(
            ["bash", self.uninstall_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        with open(settings_file) as f:
            settings = json.load(f)
        
        # Collect all handlers from nested structure
        matcher_groups = settings.get("hooks", {}).get("UserPromptSubmit", [])
        all_handlers = []
        for group in matcher_groups:
            if isinstance(group, dict) and "hooks" in group:
                all_handlers.extend(group["hooks"])
        
        # Other hook should remain
        other_handlers = [
            h for h in all_handlers
            if isinstance(h, dict) and "other hook" in h.get("command", "")
        ]
        self.assertEqual(len(other_handlers), 1)
        
        # Our hook should be removed
        our_handlers = [
            h for h in all_handlers
            if isinstance(h, dict) and "claude-auto-translate" in h.get("command", "")
        ]
        self.assertEqual(len(our_handlers), 0)
    
    def test_uninstall_removes_skill_files(self):
        """Uninstall should remove skill files."""
        # First install
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        skill_dir = os.path.join(
            self.temp_home, ".claude", "skills", "claude-auto-translate"
        )
        
        # Verify files exist
        self.assertTrue(os.path.isfile(os.path.join(skill_dir, "hook.py")))
        
        # Uninstall
        subprocess.run(
            ["bash", self.uninstall_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        # hook.py should be removed
        self.assertFalse(os.path.isfile(os.path.join(skill_dir, "hook.py")))
    
    def test_uninstall_with_keep_config(self):
        """Uninstall --keep-config should preserve config.json."""
        # First install
        subprocess.run(
            ["bash", self.install_script],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        skill_dir = os.path.join(
            self.temp_home, ".claude", "skills", "claude-auto-translate"
        )
        config_file = os.path.join(skill_dir, "config.json")
        
        # Uninstall with --keep-config
        subprocess.run(
            ["bash", self.uninstall_script, "--keep-config"],
            cwd=self.script_dir,
            capture_output=True,
            env={**os.environ, "HOME": self.temp_home}
        )
        
        # Config should still exist
        self.assertTrue(os.path.isfile(config_file))


if __name__ == "__main__":
    unittest.main()
