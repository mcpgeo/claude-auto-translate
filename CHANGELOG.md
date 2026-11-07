# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-07

### Added

- Initial release of Claude Auto-Translate skill
- `UserPromptSubmit` hook for Claude Code integration
- Language detection for non-English text (Georgian as primary target)
- Code/URL/path preservation during translation
- Support for 5 translation providers:
  - Anthropic Claude (default, using Haiku)
  - OpenAI (GPT-4o-mini)
  - Google Gemini (gemini-1.5-flash)
  - DeepL
  - Google Cloud Translation
- Two display modes: `native` and `bilingual`
- Configurable timeouts (global and per-provider)
- Enable/disable via config or environment variable
- `install.sh` for easy installation
- `uninstall.sh` for clean removal
- Idempotent installer (safe to run multiple times)
- SKILL.md for Claude Code skill discovery
- Comprehensive unit tests
- GitHub Actions CI for Ubuntu and macOS
- Documentation in English with Georgian section
