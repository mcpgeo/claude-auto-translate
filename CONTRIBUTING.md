# Contributing to Claude Auto-Translate

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/claude-auto-translate.git
   cd claude-auto-translate
   ```

2. Run tests to verify everything works:
   ```bash
   python -m unittest discover -s tests -v
   ```

## Running Tests

All tests use Python's standard `unittest` module (no dependencies required):

```bash
# Run all tests
python -m unittest discover -s tests -v

# Run specific test file
python -m unittest tests.test_detect -v

# Run specific test class
python -m unittest tests.test_detect.TestShouldTranslate -v
```

## Code Guidelines

### Python

- **Python 3 standard library only** — No pip dependencies
- Works on both macOS and Linux
- Follow PEP 8 style guidelines
- Add docstrings to public functions and classes
- Add type hints where helpful

### Shell Scripts

- Use `#!/usr/bin/env bash`
- Support both macOS and Linux (avoid GNU-specific options)
- Always use `set -e` for error handling
- Quote variables properly

## Adding a New Translation Provider

1. Create a new class in `src/providers.py` inheriting from `TranslationProvider`
2. Implement the `translate()` method
3. Add the provider to the `PROVIDERS` dict
4. Add the env var name to `ENV_VAR_NAMES` in `src/config.py`
5. Add provider config to `DEFAULT_CONFIG` in `src/config.py`
6. Add tests in `tests/test_providers.py`
7. Update README.md with the new provider

## Adding a New Language

Languages are configured by the user in `config.json`. No code changes needed for new languages unless:

- The provider requires specific language codes (add to the provider's `LANG_CODES` dict)
- The language detection needs special handling (modify `src/detect.py`)

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `python -m unittest discover -s tests -v`
5. Commit with a clear message
6. Push to your fork
7. Open a Pull Request

## Reporting Issues

When reporting bugs, please include:

- Python version (`python --version`)
- Operating system (macOS/Linux version)
- The exact prompt that caused the issue
- The expected vs actual behavior
- Any error messages from stderr

## Questions?

Open an issue with the `question` label if you need help or clarification.
