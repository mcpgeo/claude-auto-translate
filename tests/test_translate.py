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
    build_additional_context,
    build_system_message,
    process_prompt,
    MAX_CONTEXT_CHARS,
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
    
    def test_passthrough_for_very_long_prompt(self):
        """Should return None for prompts that would exceed context limit."""
        config = {"enabled": True}
        
        # Create a very long Georgian prompt
        long_prompt = "გამარჯობა " * 2000  # Well over 10,000 chars
        
        result, original = translate_prompt(long_prompt, config)
        
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


class TestBuildAdditionalContext(unittest.TestCase):
    """Test additionalContext string building."""
    
    def test_context_contains_translation(self):
        """Context should contain the translation."""
        config = {"user_language": "Georgian"}
        
        result = build_additional_context("Hello world", config)
        
        self.assertIn("Hello world", result)
        self.assertIn("Georgian", result)
        self.assertIn("Respond to the user in Georgian", result)
    
    def test_context_within_limit(self):
        """Context should be within the 10,000 char limit."""
        config = {"user_language": "Georgian"}
        
        result = build_additional_context("Hello world", config)
        
        self.assertLessEqual(len(result), MAX_CONTEXT_CHARS)


class TestBuildSystemMessage(unittest.TestCase):
    """Test systemMessage building for bilingual mode."""
    
    def test_native_mode_returns_none(self):
        """Native mode should not produce a system message."""
        config = {"display_mode": "native"}
        
        result = build_system_message("Hello", config)
        
        self.assertIsNone(result)
    
    def test_bilingual_mode_returns_message(self):
        """Bilingual mode should produce a system message."""
        config = {"display_mode": "bilingual"}
        
        result = build_system_message("Hello world", config)
        
        self.assertIsNotNone(result)
        self.assertIn("[Translation:", result)
        self.assertIn("Hello world", result)
    
    def test_bilingual_truncates_long_translation(self):
        """Bilingual mode should truncate long translations."""
        config = {"display_mode": "bilingual"}
        
        long_translation = "A" * 300
        result = build_system_message(long_translation, config)
        
        self.assertIn("...", result)
        self.assertLess(len(result), 250)


class TestBuildHookOutput(unittest.TestCase):
    """Test hook output JSON structure per Claude Code docs."""
    
    def test_output_has_correct_structure(self):
        """Output must have hookSpecificOutput with hookEventName and additionalContext."""
        config = {
            "user_language": "Georgian",
            "display_mode": "native",
        }
        
        result = build_hook_output("Hello", "გამარჯობა", config)
        
        # Verify structure matches Claude Code hooks docs
        self.assertIn("hookSpecificOutput", result)
        self.assertIn("hookEventName", result["hookSpecificOutput"])
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("additionalContext", result["hookSpecificOutput"])
    
    def test_native_mode_no_system_message(self):
        """Native mode should not include systemMessage."""
        config = {
            "user_language": "Georgian",
            "display_mode": "native",
        }
        
        result = build_hook_output("Hello", "გამარჯობა", config)
        
        self.assertNotIn("systemMessage", result)
    
    def test_bilingual_mode_includes_system_message(self):
        """Bilingual mode should include systemMessage for user display."""
        config = {
            "user_language": "Georgian",
            "display_mode": "bilingual",
        }
        
        result = build_hook_output("Hello", "გამარჯობა", config)
        
        self.assertIn("systemMessage", result)
        self.assertIn("[Translation:", result["systemMessage"])
    
    def test_output_is_json_serializable(self):
        """Output must be JSON serializable."""
        config = {
            "user_language": "Georgian",
            "display_mode": "bilingual",
        }
        
        result = build_hook_output("Hello", "გამარჯობა", config)
        
        # Should not raise
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")


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
    
    @patch("urllib.request.urlopen")
    def test_returns_correct_json_structure(self, mock_urlopen):
        """Should return dict with correct JSON structure per Claude Code docs."""
        mock_response = MockResponse({
            "content": [{"text": "Hello"}]
        })
        mock_urlopen.return_value = mock_response
        
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        
        result = process_prompt("გამარჯობა")
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn("hookSpecificOutput", result)
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("additionalContext", result["hookSpecificOutput"])


if __name__ == "__main__":
    unittest.main()
