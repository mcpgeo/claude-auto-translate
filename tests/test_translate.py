"""Tests for translation orchestration and failure passthrough."""

import json
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.translate import (
    translate_prompt,
    build_hook_output,
    process_prompt,
)


class MockResponse:
    """Mock HTTP response object."""
    
    def __init__(self, data: dict):
        self._data = json.dumps(data).encode("utf-8")
    
    def read(self):
        return self._data
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


class TestTranslatePrompt(unittest.TestCase):
    """Test the translate_prompt function."""
    
    def setUp(self):
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_passthrough_when_disabled(self):
        """Should return None when translation is disabled."""
        config = {"enabled": False}
        
        result, original = translate_prompt("გამარჯობა", config)
        
        self.assertIsNone(result)
        self.assertIsNone(original)
    
    def test_passthrough_for_english(self):
        """Should return None for English text."""
        config = {"enabled": True}
        
        result, original = translate_prompt("Hello world", config)
        
        self.assertIsNone(result)
        self.assertIsNone(original)
    
    def test_passthrough_for_code_only(self):
        """Should return None for code-only input."""
        config = {"enabled": True}
        
        result, original = translate_prompt("```python\nprint('hello')\n```", config)
        
        self.assertIsNone(result)
        self.assertIsNone(original)
    
    def test_passthrough_when_no_api_key(self):
        """Should return None when no API key is available."""
        # Clear any API keys from environment
        for key in list(os.environ.keys()):
            if "API_KEY" in key:
                del os.environ[key]
        
        config = {
            "enabled": True,
            "provider": "anthropic",
            "providers": {"anthropic": {}},
        }
        
        result, original = translate_prompt("გამარჯობა", config)
        
        self.assertIsNone(result)
        self.assertIsNone(original)
    
    @patch("urllib.request.urlopen")
    def test_successful_translation(self, mock_urlopen):
        """Should return translation on success."""
        mock_response = MockResponse({
            "content": [{"text": "Hello"}]
        })
        mock_urlopen.return_value = mock_response
        
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        
        config = {
            "enabled": True,
            "provider": "anthropic",
            "user_language": "Georgian",
            "working_language": "English",
            "timeout_seconds": 10,
            "providers": {"anthropic": {"model": "claude-3-haiku-20240307"}},
        }
        
        result, original = translate_prompt("გამარჯობა", config)
        
        self.assertEqual(result, "Hello")
        self.assertEqual(original, "გამარჯობა")
    
    @patch("urllib.request.urlopen")
    def test_passthrough_on_network_error(self, mock_urlopen):
        """Should return None on network error."""
        mock_urlopen.side_effect = Exception("Network error")
        
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        
        config = {
            "enabled": True,
            "provider": "anthropic",
            "user_language": "Georgian",
            "working_language": "English",
            "timeout_seconds": 10,
            "providers": {"anthropic": {"model": "claude-3-haiku-20240307"}},
        }
        
        result, original = translate_prompt("გამარჯობა", config)
        
        self.assertIsNone(result)
        self.assertIsNone(original)
    
    @patch("urllib.request.urlopen")
    def test_passthrough_on_empty_response(self, mock_urlopen):
        """Should return None when translation response is empty."""
        mock_response = MockResponse({"content": []})
        mock_urlopen.return_value = mock_response
        
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        
        config = {
            "enabled": True,
            "provider": "anthropic",
            "user_language": "Georgian",
            "working_language": "English",
            "timeout_seconds": 10,
            "providers": {"anthropic": {}},
        }
        
        result, original = translate_prompt("გამარჯობა", config)
        
        self.assertIsNone(result)
        self.assertIsNone(original)


class TestBuildHookOutput(unittest.TestCase):
    """Test hook output building."""
    
    def test_native_mode_output(self):
        """Native mode should not include translation acknowledgment."""
        config = {
            "user_language": "Georgian",
            "display_mode": "native",
        }
        
        result = build_hook_output("Hello", "გამარჯობა", config)
        
        self.assertIn("[Translation Context]", result)
        self.assertIn("Hello", result)
        self.assertIn("Georgian", result)
        self.assertIn("Respond to the user in Georgian", result)
        self.assertNotIn("acknowledge the translation", result)
    
    def test_bilingual_mode_output(self):
        """Bilingual mode should include translation acknowledgment."""
        config = {
            "user_language": "Georgian",
            "display_mode": "bilingual",
        }
        
        result = build_hook_output("Hello", "გამარჯობა", config)
        
        self.assertIn("[Translation Context]", result)
        self.assertIn("acknowledge the translation", result)


class TestProcessPrompt(unittest.TestCase):
    """Test the main hook entry point."""
    
    def setUp(self):
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_returns_none_for_english(self):
        """Should return None for English prompts."""
        result = process_prompt("Hello, how can I help?")
        self.assertIsNone(result)
    
    def test_returns_none_when_disabled_via_env(self):
        """Should return None when disabled via environment."""
        os.environ["CLAUDE_AUTO_TRANSLATE_ENABLED"] = "false"
        
        result = process_prompt("გამარჯობა")
        
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
