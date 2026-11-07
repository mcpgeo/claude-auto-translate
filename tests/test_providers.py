"""Tests for translation providers with mocked HTTP."""

import json
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.providers import (
    AnthropicProvider,
    OpenAIProvider,
    GeminiProvider,
    DeepLProvider,
    GoogleCloudProvider,
    get_provider,
    PROVIDERS,
)


class MockResponse:
    """Mock HTTP response object."""
    
    def __init__(self, data: dict, status: int = 200):
        self._data = json.dumps(data).encode("utf-8")
        self.status = status
    
    def read(self):
        return self._data
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


class TestAnthropicProvider(unittest.TestCase):
    """Test Anthropic translation provider."""
    
    def setUp(self):
        self.provider = AnthropicProvider(
            api_key="test-key",
            config={"model": "claude-3-haiku-20240307"},
            timeout=10
        )
    
    @patch("urllib.request.urlopen")
    def test_translate_builds_correct_request(self, mock_urlopen):
        """Verify request payload structure."""
        mock_response = MockResponse({
            "content": [{"text": "Hello"}]
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        # Verify urlopen was called
        self.assertTrue(mock_urlopen.called)
        
        # Get the request object
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        # Verify headers
        self.assertEqual(request.get_header("X-api-key"), "test-key")
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
        
        # Verify payload
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "claude-3-haiku-20240307")
        self.assertIn("messages", payload)
    
    @patch("urllib.request.urlopen")
    def test_translate_extracts_response(self, mock_urlopen):
        """Verify response text extraction."""
        mock_response = MockResponse({
            "content": [{"text": "  Hello  "}]
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        self.assertEqual(result, "Hello")
    
    @patch("urllib.request.urlopen")
    def test_translate_handles_empty_response(self, mock_urlopen):
        """Handle empty content array."""
        mock_response = MockResponse({"content": []})
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        self.assertEqual(result, "")


class TestOpenAIProvider(unittest.TestCase):
    """Test OpenAI translation provider."""
    
    def setUp(self):
        self.provider = OpenAIProvider(
            api_key="test-key",
            config={"model": "gpt-4o-mini"},
            timeout=10
        )
    
    @patch("urllib.request.urlopen")
    def test_translate_builds_correct_request(self, mock_urlopen):
        """Verify request payload structure."""
        mock_response = MockResponse({
            "choices": [{"message": {"content": "Hello"}}]
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        # Verify authorization header
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        
        # Verify payload has system message
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(len(payload["messages"]), 2)  # system + user
    
    @patch("urllib.request.urlopen")
    def test_translate_extracts_response(self, mock_urlopen):
        """Verify response text extraction."""
        mock_response = MockResponse({
            "choices": [{"message": {"content": "  Hello world  "}}]
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        self.assertEqual(result, "Hello world")


class TestGeminiProvider(unittest.TestCase):
    """Test Google Gemini translation provider."""
    
    def setUp(self):
        self.provider = GeminiProvider(
            api_key="test-key",
            config={"model": "gemini-1.5-flash"},
            timeout=10
        )
    
    @patch("urllib.request.urlopen")
    def test_translate_builds_correct_url(self, mock_urlopen):
        """Verify API URL includes model and key."""
        mock_response = MockResponse({
            "candidates": [{"content": {"parts": [{"text": "Hello"}]}}]
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        # Verify URL contains model and key
        self.assertIn("gemini-1.5-flash", request.full_url)
        self.assertIn("key=test-key", request.full_url)
    
    @patch("urllib.request.urlopen")
    def test_translate_extracts_response(self, mock_urlopen):
        """Verify response text extraction."""
        mock_response = MockResponse({
            "candidates": [{
                "content": {
                    "parts": [{"text": "  Hello  "}]
                }
            }]
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        self.assertEqual(result, "Hello")


class TestDeepLProvider(unittest.TestCase):
    """Test DeepL translation provider."""
    
    def setUp(self):
        self.provider = DeepLProvider(
            api_key="test-key",
            config={},
            timeout=10
        )
    
    @patch("urllib.request.urlopen")
    def test_translate_uses_pro_api(self, mock_urlopen):
        """Non-free key should use pro API."""
        mock_response = MockResponse({
            "translations": [{"text": "Hello"}]
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        self.assertIn("api.deepl.com", request.full_url)
    
    @patch("urllib.request.urlopen")
    def test_translate_uses_free_api(self, mock_urlopen):
        """Free key (with :fx) should use free API."""
        provider = DeepLProvider(
            api_key="test-key:fx",
            config={},
            timeout=10
        )
        
        mock_response = MockResponse({
            "translations": [{"text": "Hello"}]
        })
        mock_urlopen.return_value = mock_response
        
        result = provider.translate("გამარჯობა", "Georgian", "English")
        
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        self.assertIn("api-free.deepl.com", request.full_url)
    
    @patch("urllib.request.urlopen")
    def test_translate_extracts_response(self, mock_urlopen):
        """Verify response text extraction."""
        mock_response = MockResponse({
            "translations": [{"text": "Hello world"}]
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        self.assertEqual(result, "Hello world")


class TestGoogleCloudProvider(unittest.TestCase):
    """Test Google Cloud Translation provider."""
    
    def setUp(self):
        self.provider = GoogleCloudProvider(
            api_key="test-key",
            config={},
            timeout=10
        )
    
    @patch("urllib.request.urlopen")
    def test_translate_builds_correct_request(self, mock_urlopen):
        """Verify request payload structure."""
        mock_response = MockResponse({
            "data": {"translations": [{"translatedText": "Hello"}]}
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        payload = json.loads(request.data.decode("utf-8"))
        self.assertIn("key", payload)
        self.assertEqual(payload["target"], "en")
    
    @patch("urllib.request.urlopen")
    def test_translate_extracts_response(self, mock_urlopen):
        """Verify response text extraction."""
        mock_response = MockResponse({
            "data": {"translations": [{"translatedText": "  Hello  "}]}
        })
        mock_urlopen.return_value = mock_response
        
        result = self.provider.translate("გამარჯობა", "Georgian", "English")
        
        self.assertEqual(result, "Hello")


class TestGetProvider(unittest.TestCase):
    """Test provider factory function."""
    
    def test_get_anthropic_provider(self):
        provider = get_provider("anthropic", "key", {}, 10)
        self.assertIsInstance(provider, AnthropicProvider)
    
    def test_get_openai_provider(self):
        provider = get_provider("openai", "key", {}, 10)
        self.assertIsInstance(provider, OpenAIProvider)
    
    def test_get_gemini_provider(self):
        provider = get_provider("gemini", "key", {}, 10)
        self.assertIsInstance(provider, GeminiProvider)
    
    def test_get_deepl_provider(self):
        provider = get_provider("deepl", "key", {}, 10)
        self.assertIsInstance(provider, DeepLProvider)
    
    def test_get_google_cloud_provider(self):
        provider = get_provider("google_cloud", "key", {}, 10)
        self.assertIsInstance(provider, GoogleCloudProvider)
    
    def test_get_unknown_provider(self):
        provider = get_provider("unknown", "key", {}, 10)
        self.assertIsNone(provider)
    
    def test_all_providers_registered(self):
        """Verify all expected providers are in PROVIDERS dict."""
        expected = ["anthropic", "openai", "gemini", "deepl", "google_cloud"]
        for name in expected:
            self.assertIn(name, PROVIDERS)


if __name__ == "__main__":
    unittest.main()
