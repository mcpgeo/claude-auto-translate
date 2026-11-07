"""Configuration loading and validation for claude-auto-translate."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG = {
    "enabled": True,
    "user_language": "Georgian",
    "working_language": "English",
    "display_mode": "native",  # "native" or "bilingual"
    "provider": "anthropic",
    "timeout_seconds": 10,
    "providers": {
        "anthropic": {
            "model": "claude-3-haiku-20240307",
            "timeout_seconds": None,  # Use global timeout if None
        },
        "openai": {
            "model": "gpt-4o-mini",
            "timeout_seconds": None,
        },
        "gemini": {
            "model": "gemini-1.5-flash",
            "timeout_seconds": None,
        },
        "deepl": {
            "timeout_seconds": None,
        },
        "google_cloud": {
            "timeout_seconds": None,
        },
    },
}

ENV_VAR_NAMES = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepl": "DEEPL_API_KEY",
    "google_cloud": "GOOGLE_CLOUD_API_KEY",
}

SKILL_NAME = "claude-auto-translate"


def get_config_paths() -> list[Path]:
    """Return potential config file paths in priority order."""
    paths = []
    
    # Project-level config (highest priority)
    cwd = Path.cwd()
    paths.append(cwd / ".claude" / SKILL_NAME / "config.json")
    
    # User-level config
    home = Path.home()
    paths.append(home / ".claude" / "skills" / SKILL_NAME / "config.json")
    
    return paths


def load_config() -> Dict[str, Any]:
    """Load configuration from file, merging with defaults."""
    config = DEFAULT_CONFIG.copy()
    config["providers"] = {k: v.copy() for k, v in DEFAULT_CONFIG["providers"].items()}
    
    for config_path in get_config_paths():
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                config = _merge_config(config, user_config)
                break  # Use first found config
            except (json.JSONDecodeError, IOError):
                pass  # Ignore malformed configs, use defaults
    
    # Check for enable/disable env var override
    env_enabled = os.environ.get("CLAUDE_AUTO_TRANSLATE_ENABLED")
    if env_enabled is not None:
        config["enabled"] = env_enabled.lower() in ("1", "true", "yes", "on")
    
    return config


def _merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge override into base config."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result


def get_api_key(provider: str, config: Dict[str, Any]) -> Optional[str]:
    """Get API key for provider from env var or config."""
    # Environment variable takes precedence
    env_var = ENV_VAR_NAMES.get(provider)
    if env_var:
        key = os.environ.get(env_var)
        if key:
            return key
    
    # Fall back to config file
    provider_config = config.get("providers", {}).get(provider, {})
    return provider_config.get("api_key")


def get_timeout(provider: str, config: Dict[str, Any]) -> float:
    """Get timeout for provider, falling back to global timeout."""
    provider_config = config.get("providers", {}).get(provider, {})
    timeout = provider_config.get("timeout_seconds")
    if timeout is not None:
        return float(timeout)
    return float(config.get("timeout_seconds", 10))


def is_enabled(config: Dict[str, Any]) -> bool:
    """Check if translation is enabled."""
    return config.get("enabled", True)
