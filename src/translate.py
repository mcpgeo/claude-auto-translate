"""Main translation orchestration for claude-auto-translate."""

import json
import sys
from typing import Any, Dict, Optional, Tuple

from .config import get_api_key, get_timeout, is_enabled, load_config
from .detect import (
    extract_preservables,
    restore_preservables,
    should_translate,
)
from .providers import get_provider

# Claude Code caps additionalContext at 10,000 characters
MAX_CONTEXT_CHARS = 10000
# Reserve some chars for the wrapper text
CONTEXT_OVERHEAD = 500


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
    
    # Skip very long prompts that would exceed context limit after translation
    max_translatable = MAX_CONTEXT_CHARS - CONTEXT_OVERHEAD
    if len(prompt) > max_translatable:
        warn(f"Prompt too long ({len(prompt)} chars, max {max_translatable}). Passing through unchanged.")
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


def build_additional_context(
    translated: str,
    config: Dict[str, Any]
) -> str:
    """
    Build the additionalContext string for Claude.
    
    Args:
        translated: The English translation of the prompt
        config: Configuration dict
    
    Returns:
        The context string to inject via additionalContext
    """
    user_lang = config.get("user_language", "Georgian")
    
    # Build the context for Claude (this goes into additionalContext)
    context = (
        f"The user wrote their prompt in {user_lang}. "
        f"Here is the English translation:\n\n"
        f"{translated}\n\n"
        f"IMPORTANT: Respond to the user in {user_lang}."
    )
    
    # Truncate if needed (should rarely happen due to earlier check)
    if len(context) > MAX_CONTEXT_CHARS:
        truncate_at = MAX_CONTEXT_CHARS - 100
        context = context[:truncate_at] + "\n\n[Translation truncated due to length]"
    
    return context


def build_system_message(
    translated: str,
    config: Dict[str, Any]
) -> Optional[str]:
    """
    Build the systemMessage for bilingual mode (shown to user).
    
    Args:
        translated: The English translation of the prompt
        config: Configuration dict
    
    Returns:
        The system message to show to user, or None if not in bilingual mode
    """
    display_mode = config.get("display_mode", "native")
    
    if display_mode != "bilingual":
        return None
    
    # Truncate long translations for display
    if len(translated) > 200:
        display_translation = translated[:197] + "..."
    else:
        display_translation = translated
    
    return f"[Translation: {display_translation}]"


def build_hook_output(
    translated: str,
    original: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build the complete hook output JSON object.
    
    Per Claude Code hooks docs, UserPromptSubmit hooks output:
    {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "..."
        },
        "systemMessage": "..."  // optional, shown to user
    }
    
    Args:
        translated: The English translation of the prompt
        original: The original prompt in user's language
        config: Configuration dict
    
    Returns:
        The hook output dict to be JSON-serialized
    """
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": build_additional_context(translated, config)
        }
    }
    
    # Add systemMessage for bilingual mode (shown to user in transcript)
    system_msg = build_system_message(translated, config)
    if system_msg:
        output["systemMessage"] = system_msg
    
    return output


def process_prompt(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Main entry point for hook processing.
    
    Args:
        prompt: The user's prompt text
    
    Returns:
        Hook output dict to be JSON-serialized, or None if no translation needed/possible.
    """
    config = load_config()
    
    translated, original = translate_prompt(prompt, config)
    
    if translated is None:
        return None
    
    return build_hook_output(translated, original, config)
