"""Language detection and code/URL preservation for claude-auto-translate."""

import re
from typing import List, Tuple

# Regex patterns for content that should not be translated
PLACEHOLDER_PATTERNS = [
    # Code blocks (fenced with ``` or ~~~)
    (r'```[\s\S]*?```', 'CODEBLOCK'),
    (r'~~~[\s\S]*?~~~', 'CODEBLOCK'),
    # Inline code (backticks)
    (r'`[^`\n]+`', 'INLINECODE'),
    # URLs (http, https, ftp, file)
    (r'https?://[^\s<>\[\]()]+', 'URL'),
    (r'ftp://[^\s<>\[\]()]+', 'URL'),
    (r'file://[^\s<>\[\]()]+', 'URL'),
    # File paths (Unix and Windows style)
    (r'(?:^|(?<=\s))(?:/[\w./-]+|~[\w./-]*)', 'FILEPATH'),
    (r'(?:^|(?<=\s))[A-Za-z]:\\[\w.\\/-]+', 'FILEPATH'),
    (r'(?:^|(?<=\s))\.{1,2}/[\w./-]+', 'FILEPATH'),
    # Common programming identifiers (camelCase, snake_case, CONSTANT_CASE)
    (r'\b[a-z]+(?:[A-Z][a-z]*)+\b', 'IDENT'),  # camelCase
    (r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', 'IDENT'),  # PascalCase
    (r'\b[a-z]+(?:_[a-z]+)+\b', 'IDENT'),  # snake_case
    (r'\b[A-Z]+(?:_[A-Z]+)+\b', 'IDENT'),  # CONSTANT_CASE
]


def extract_preservables(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Extract code blocks, URLs, file paths, and identifiers from text.
    
    Returns:
        Tuple of (text_with_placeholders, list_of_preserved_items)
        Each preserved item is (placeholder_id, original_text)
    """
    preserved = []
    result = text
    counter = 0
    
    for pattern, ptype in PLACEHOLDER_PATTERNS:
        def replace_match(match):
            nonlocal counter
            original = match.group(0)
            placeholder = f"__PRESERVE_{ptype}_{counter}__"
            preserved.append((placeholder, original))
            counter += 1
            return placeholder
        
        result = re.sub(pattern, replace_match, result)
    
    return result, preserved


def restore_preservables(text: str, preserved: List[Tuple[str, str]]) -> str:
    """Restore preserved content back into translated text."""
    result = text
    for placeholder, original in preserved:
        result = result.replace(placeholder, original)
    return result


def is_primarily_ascii(text: str, threshold: float = 0.85) -> bool:
    """
    Check if text is primarily ASCII characters.
    
    Used to detect if text is likely English/code-only.
    """
    if not text:
        return True
    
    # Remove common preserved patterns first for cleaner analysis
    clean_text = text
    for pattern, _ in PLACEHOLDER_PATTERNS:
        clean_text = re.sub(pattern, ' ', clean_text)
    
    # Remove whitespace and punctuation for analysis
    clean_text = re.sub(r'[\s\d\W]+', '', clean_text)
    
    if not clean_text:
        return True
    
    ascii_count = sum(1 for c in clean_text if ord(c) < 128)
    return (ascii_count / len(clean_text)) >= threshold


def is_code_only(text: str) -> bool:
    """
    Check if text appears to be purely code (no natural language).
    
    Looks for indicators like:
    - Only code blocks
    - No alphabetic characters outside code patterns
    """
    # Strip whitespace
    stripped = text.strip()
    
    # Check if entire text is a code block
    if (stripped.startswith('```') and stripped.endswith('```')) or \
       (stripped.startswith('~~~') and stripped.endswith('~~~')):
        return True
    
    # Check if text is just inline code
    if stripped.startswith('`') and stripped.endswith('`') and stripped.count('`') == 2:
        return True
    
    # Remove all preserved patterns
    clean_text = stripped
    for pattern, _ in PLACEHOLDER_PATTERNS:
        clean_text = re.sub(pattern, '', clean_text)
    
    # Remove whitespace and punctuation
    clean_text = re.sub(r'[\s\W]+', '', clean_text)
    
    # If nothing remains, it was all code/URLs/paths
    return len(clean_text) == 0


def contains_non_latin_script(text: str) -> bool:
    """
    Check if text contains non-Latin script characters.
    
    This is a simple heuristic to detect non-English text.
    Checks for characters outside basic Latin + extended Latin ranges.
    """
    # Remove preserved content for cleaner analysis
    clean_text = text
    for pattern, _ in PLACEHOLDER_PATTERNS:
        clean_text = re.sub(pattern, ' ', clean_text)
    
    # Check for non-Latin characters
    for char in clean_text:
        code = ord(char)
        # Skip whitespace, digits, punctuation
        if char.isspace() or char.isdigit() or not char.isalpha():
            continue
        # Check if outside Latin range (basic Latin + Latin Extended)
        if code > 0x024F:  # Beyond Latin Extended-B
            return True
    
    return False


def should_translate(text: str) -> bool:
    """
    Determine if text should be translated.
    
    Returns False for:
    - Empty or whitespace-only text
    - Code-only text
    - Primarily ASCII text (likely English or code)
    
    Returns True for:
    - Text containing non-Latin scripts
    - Text with significant non-ASCII content
    """
    if not text or not text.strip():
        return False
    
    if is_code_only(text):
        return False
    
    # If it contains non-Latin script, it should be translated
    if contains_non_latin_script(text):
        return True
    
    # If primarily ASCII, don't translate (assume English)
    if is_primarily_ascii(text):
        return False
    
    return True
