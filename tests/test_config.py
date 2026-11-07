"""Tests for configuration loading."""

import json
import os
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import (
    DEFAULT_CONFIG,
    ENV_VAR_NAMES,
    load_config,
    get_api_key,
    get_timeout,
    is_enabled,
    _merge_config,
)


class TestMergeConfig(unittest.TestCase):
    """Test configuration merging."""
    
    def test_merge_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        result = _merge_config(base, override)
        
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 3)
    
    def test_merge_nested_dict(self):
        base = {"outer": {"inner": 1, "other": 2}}
        override = {"outer": {"inner": 10}}
        result = _merge_config(base, override)
        
        self.assertEqual(result["outer"]["inner"], 10)
        self.assertEqual(result["outer"]["other"], 2)
    
    def test_merge_add_new_key(self):
        base = {"a": 1}
        override = {"b": 2}
        result = _merge_config(base, override)
        
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 2)


class TestLoadConfig(unittest.TestCase):
    """Test loading configuration from files and environment."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.original_env = os.environ.copy()
        # Clear any test-affecting env vars
        for key in list(os.environ.keys()):
            if key.startswith("CLAUDE_AUTO_TRANSLATE"):
                del os.environ[key]
    
    def tearDown(self):
        """Restore environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_load_default_when_no_file(self):
        """Should return defaults when no config file exists."""
        # This test assumes no config file in standard locations
        # during testing
        config = load_config()
        
        self.assertTrue(config.get("enabled"))
        self.assertEqual(config.get("provider"), "anthropic")
    
    def test_env_var_override_enabled(self):
        """Environment variable should override config enabled setting."""
        os.environ["CLAUDE_AUTO_TRANSLATE_ENABLED"] = "false"
        config = load_config()
        
        self.assertFalse(config.get("enabled"))
    
    def test_env_var_enabled_variations(self):
        """Test various truthy/falsy values for enabled env var."""
        for value, expected in [
            ("1", True),
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("yes", True),
            ("YES", True),
            ("on", True),
            ("0", False),
            ("false", False),
            ("False", False),
            ("no", False),
            ("off", False),
        ]:
            os.environ["CLAUDE_AUTO_TRANSLATE_ENABLED"] = value
            config = load_config()
            self.assertEqual(
                config.get("enabled"),
                expected,
                f"Failed for value '{value}'"
            )


class TestGetApiKey(unittest.TestCase):
    """Test API key retrieval."""
    
    def setUp(self):
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_get_from_env_var(self):
        """API key from environment variable takes precedence."""
        os.environ["ANTHROPIC_API_KEY"] = "env-key-123"
        config = {"providers": {"anthropic": {"api_key": "config-key"}}}
        
        key = get_api_key("anthropic", config)
        
        self.assertEqual(key, "env-key-123")
    
    def test_get_from_config_when_no_env(self):
        """Fall back to config file when no env var."""
        # Ensure env var is not set
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        config = {"providers": {"anthropic": {"api_key": "config-key"}}}
        key = get_api_key("anthropic", config)
        
        self.assertEqual(key, "config-key")
    
    def test_return_none_when_no_key(self):
        """Return None when no key available."""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        config = {"providers": {"openai": {}}}
        key = get_api_key("openai", config)
        
        self.assertIsNone(key)
    
    def test_all_env_var_names(self):
        """Verify all provider env var names are defined."""
        expected_providers = ["anthropic", "openai", "gemini", "deepl", "google_cloud"]
        
        for provider in expected_providers:
            self.assertIn(provider, ENV_VAR_NAMES)


class TestGetTimeout(unittest.TestCase):
    """Test timeout configuration."""
    
    def test_provider_specific_timeout(self):
        """Provider-specific timeout overrides global."""
        config = {
            "timeout_seconds": 10,
            "providers": {"anthropic": {"timeout_seconds": 20}},
        }
        
        timeout = get_timeout("anthropic", config)
        
        self.assertEqual(timeout, 20)
    
    def test_global_timeout_fallback(self):
        """Fall back to global timeout when provider has none."""
        config = {
            "timeout_seconds": 15,
            "providers": {"anthropic": {"timeout_seconds": None}},
        }
        
        timeout = get_timeout("anthropic", config)
        
        self.assertEqual(timeout, 15)
    
    def test_default_timeout(self):
        """Default timeout when not configured."""
        config = {"providers": {}}
        
        timeout = get_timeout("anthropic", config)
        
        self.assertEqual(timeout, 10)  # Default


class TestIsEnabled(unittest.TestCase):
    """Test enabled checking."""
    
    def test_enabled_true(self):
        self.assertTrue(is_enabled({"enabled": True}))
    
    def test_enabled_false(self):
        self.assertFalse(is_enabled({"enabled": False}))
    
    def test_default_enabled(self):
        """Default to enabled when not specified."""
        self.assertTrue(is_enabled({}))


if __name__ == "__main__":
    unittest.main()
