"""Tests for language detection and code preservation."""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detect import (
    extract_preservables,
    restore_preservables,
    is_primarily_ascii,
    is_code_only,
    contains_non_latin_script,
    should_translate,
)


class TestExtractPreservables(unittest.TestCase):
    """Test extraction of code blocks, URLs, paths, and identifiers."""
    
    def test_preserves_code_blocks(self):
        text = "Here is code:\n```python\nprint('hello')\n```"
        result, preserved = extract_preservables(text)
        
        self.assertIn("__PRESERVE_CODEBLOCK_", result)
        self.assertEqual(len(preserved), 1)
        self.assertIn("```python", preserved[0][1])
    
    def test_preserves_inline_code(self):
        text = "Use `git commit` to save"
        result, preserved = extract_preservables(text)
        
        self.assertIn("__PRESERVE_INLINECODE_", result)
        self.assertEqual(preserved[0][1], "`git commit`")
    
    def test_preserves_urls(self):
        text = "Visit https://example.com/path?query=1 for info"
        result, preserved = extract_preservables(text)
        
        self.assertIn("__PRESERVE_URL_", result)
        self.assertIn("https://example.com", preserved[0][1])
    
    def test_preserves_file_paths_unix(self):
        text = "Edit the file /home/user/config.json"
        result, preserved = extract_preservables(text)
        
        self.assertIn("__PRESERVE_FILEPATH_", result)
    
    def test_preserves_relative_paths(self):
        text = "Look at ./src/main.py"
        result, preserved = extract_preservables(text)
        
        self.assertIn("__PRESERVE_FILEPATH_", result)
    
    def test_preserves_camel_case(self):
        text = "The function getUserName returns a string"
        result, preserved = extract_preservables(text)
        
        # Should preserve getUserName
        found = any("getUserName" in p[1] for p in preserved)
        self.assertTrue(found)
    
    def test_preserves_snake_case(self):
        text = "Call the get_user_name function"
        result, preserved = extract_preservables(text)
        
        found = any("get_user_name" in p[1] for p in preserved)
        self.assertTrue(found)
    
    def test_multiple_preservables(self):
        text = "See https://docs.com and `code` and /path/file"
        result, preserved = extract_preservables(text)
        
        self.assertGreaterEqual(len(preserved), 3)


class TestRestorePreservables(unittest.TestCase):
    """Test restoration of preserved content."""
    
    def test_restore_single(self):
        preserved = [("__PRESERVE_URL_0__", "https://example.com")]
        text = "Visit __PRESERVE_URL_0__ for details"
        
        result = restore_preservables(text, preserved)
        
        self.assertEqual(result, "Visit https://example.com for details")
    
    def test_restore_multiple(self):
        preserved = [
            ("__PRESERVE_URL_0__", "https://a.com"),
            ("__PRESERVE_CODE_1__", "`test`"),
        ]
        text = "__PRESERVE_URL_0__ and __PRESERVE_CODE_1__"
        
        result = restore_preservables(text, preserved)
        
        self.assertEqual(result, "https://a.com and `test`")
    
    def test_restore_empty(self):
        result = restore_preservables("no placeholders", [])
        self.assertEqual(result, "no placeholders")


class TestIsPrimarilyAscii(unittest.TestCase):
    """Test ASCII detection."""
    
    def test_english_is_ascii(self):
        self.assertTrue(is_primarily_ascii("Hello world"))
    
    def test_code_is_ascii(self):
        self.assertTrue(is_primarily_ascii("def foo(): return 42"))
    
    def test_georgian_is_not_ascii(self):
        self.assertFalse(is_primarily_ascii("გამარჯობა"))
    
    def test_mixed_mostly_ascii(self):
        # Mostly English with a few non-ASCII chars
        text = "Hello world გ"  # One Georgian char
        # This might pass or fail depending on threshold
        result = is_primarily_ascii(text, threshold=0.85)
        # With 12 chars and 1 non-ASCII, ratio is 11/12 = 0.916
        self.assertTrue(result)
    
    def test_empty_is_ascii(self):
        self.assertTrue(is_primarily_ascii(""))
    
    def test_whitespace_is_ascii(self):
        self.assertTrue(is_primarily_ascii("   \n\t  "))


class TestIsCodeOnly(unittest.TestCase):
    """Test code-only detection."""
    
    def test_code_block_only(self):
        text = "```python\nprint('hello')\n```"
        self.assertTrue(is_code_only(text))
    
    def test_inline_code_only(self):
        text = "`git commit`"
        self.assertTrue(is_code_only(text))
    
    def test_url_only(self):
        text = "https://example.com/path"
        self.assertTrue(is_code_only(text))
    
    def test_mixed_not_code_only(self):
        text = "Please run this: `git commit`"
        self.assertFalse(is_code_only(text))
    
    def test_natural_language_not_code(self):
        text = "How do I fix this bug?"
        self.assertFalse(is_code_only(text))


class TestContainsNonLatinScript(unittest.TestCase):
    """Test non-Latin script detection."""
    
    def test_georgian(self):
        self.assertTrue(contains_non_latin_script("გამარჯობა"))
    
    def test_russian(self):
        self.assertTrue(contains_non_latin_script("Привет"))
    
    def test_chinese(self):
        self.assertTrue(contains_non_latin_script("你好"))
    
    def test_japanese(self):
        self.assertTrue(contains_non_latin_script("こんにちは"))
    
    def test_korean(self):
        self.assertTrue(contains_non_latin_script("안녕하세요"))
    
    def test_arabic(self):
        self.assertTrue(contains_non_latin_script("مرحبا"))
    
    def test_english_no_non_latin(self):
        self.assertFalse(contains_non_latin_script("Hello world"))
    
    def test_code_no_non_latin(self):
        self.assertFalse(contains_non_latin_script("def foo(): return 42"))
    
    def test_mixed_with_non_latin(self):
        self.assertTrue(contains_non_latin_script("Hello გამარჯობა"))


class TestShouldTranslate(unittest.TestCase):
    """Test the main should_translate decision function."""
    
    def test_empty_no_translate(self):
        self.assertFalse(should_translate(""))
        self.assertFalse(should_translate("   "))
    
    def test_english_no_translate(self):
        self.assertFalse(should_translate("Hello, how are you?"))
        self.assertFalse(should_translate("Please explain this code."))
    
    def test_code_only_no_translate(self):
        self.assertFalse(should_translate("```python\nprint('hello')\n```"))
        self.assertFalse(should_translate("`git status`"))
    
    def test_url_only_no_translate(self):
        self.assertFalse(should_translate("https://example.com"))
    
    def test_georgian_should_translate(self):
        self.assertTrue(should_translate("გთხოვთ ამიხსენით ეს კოდი"))
    
    def test_russian_should_translate(self):
        self.assertTrue(should_translate("Объясните этот код"))
    
    def test_mixed_with_code_should_translate(self):
        text = "გთხოვთ ამიხსენით `git commit`"
        self.assertTrue(should_translate(text))


if __name__ == "__main__":
    unittest.main()
