"""Main translation orchestration for claude-auto-translate."""

import sys
from typing import Any, Dict, Optional, Tuple

from .config import get_api_key, get_timeout, is_enabled, load_config
from .detect import (
    extract_preservables,
    restore_preservables,
    should_translate,
)
from .providers import get_provider


def warn(message: str) -> None:
    """Write a warning to stderr."""
    print(f"[claude-auto-translate] {message}", file=sys.stderr)


def translate_prompt(
    prompt: str,
    config: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Translate a user prompt if needed.
    
    Args:
        prompt: The user's prompt text
        config: Optional config dict (loads from file if not provided)
    
    Returns:
        Tuple of (translated_text, original_text) or (None, None) if no translation needed.
        Returns (None, None) on any failure, allowing original prompt through.
    """
    if config is None:
        config = load_config()
    
    # Check if translation is enabled
    if not is_enabled(config):
        return None, None
    
    # Check if text needs translation
    if not should_translate(prompt):
        return None, None
    
    # Get provider configuration
    provider_name = config.get("provider", "anthropic")
    api_key = get_api_key(provider_name, config)
    
    if not api_key:
        warn(f"No API key for provider '{provider_name}'. Passing through unchanged.")
        return None, None
    
    timeout = get_timeout(provider_name, config)
    provider_config = config.get("providers", {}).get(provider_name, {})
    
    # Get provider instance
    provider = get_provider(provider_name, api_key, provider_config, timeout)
    if not provider:
        warn(f"Unknown provider '{provider_name}'. Passing through unchanged.")
        return None, None
    
    # Get language settings
    user_lang = config.get("user_language", "Georgian")
    working_lang = config.get("working_language", "English")
    
    try:
        # Extract content that should not be translated
        text_with_placeholders, preserved = extract_preservables(prompt)
        
        # Translate
        translated = provider.translate(text_with_placeholders, user_lang, working_lang)
        
        if not translated:
            warn("Empty translation response. Passing through unchanged.")
            return None, None
        
        # Restore preserved content
        translated = restore_preservables(translated, preserved)
        
        return translated, prompt
    
    except Exception as e:
        warn(f"Translation failed: {e}. Passing through unchanged.")
        return None, None


def build_hook_output(
    translated: str,
    original: str,
    config: Dict[str, Any]
) -> str:
    """
    Build the output to inject into Claude's context.
    
    Args:
        translated: The English translation of the prompt
        original: The original prompt in user's language
        config: Configuration dict
    
    Returns:
        The formatted output to return from the hook
    """
    user_lang = config.get("user_language", "Georgian")
    display_mode = config.get("display_mode", "native")
    
    # Build the instruction for Claude
    instruction = (
        f"[Translation Context]\n"
        f"The user wrote their prompt in {user_lang}. "
        f"Here is the English translation of their prompt:\n\n"
        f"{translated}\n\n"
        f"IMPORTANT: Respond to the user in {user_lang}. "
        f"This is their preferred language."
    )
    
    if display_mode == "bilingual":
        instruction += (
            f"\n\nAt the start of your response, briefly acknowledge the translation "
            f"by showing: \"[Translation: {translated[:100]}{'...' if len(translated) > 100 else ''}]\""
        )
    
    return instruction


def process_prompt(prompt: str) -> Optional[str]:
    """
    Main entry point for hook processing.
    
    Args:
        prompt: The user's prompt text
    
    Returns:
        Context to inject, or None if no translation needed/possible.
    """
    config = load_config()
    
    translated, original = translate_prompt(prompt, config)
    
    if translated is None:
        return None
    
    return build_hook_output(translated, original, config)
