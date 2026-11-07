# Claude Auto-Translate

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/YOUR_USERNAME/claude-auto-translate/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/claude-auto-translate/actions/workflows/ci.yml)

**Use Claude Code in your native language.** This skill automatically translates your prompts to English (the optimal AI working language) while instructing Claude to respond in your native language.

## Why?

Large language models like Claude perform best when prompted in English. However, many developers think and communicate more naturally in their native language. This skill bridges that gap:

1. **Write prompts in your language** — Express your thoughts naturally
2. **Claude receives English** — Gets the translation for optimal understanding
3. **Claude replies in your language** — You read responses in your native language
4. **Code stays code** — Code blocks, URLs, file paths, and identifiers are never translated

The result: Better AI responses while you work in the language you're most comfortable with.

## Demo Example

**You type (Georgian):**
```
გთხოვთ ამიხსენით რას აკეთებს ეს ფუნქცია:
`def factorial(n): return 1 if n <= 1 else n * factorial(n-1)`
```

**Claude receives (English translation + context):**
```
[Translation Context]
The user wrote their prompt in Georgian. Here is the English translation:

Please explain what this function does:
`def factorial(n): return 1 if n <= 1 else n * factorial(n-1)`

IMPORTANT: Respond to the user in Georgian.
```

**Claude replies (Georgian):**
```
ეს ფუნქცია ითვლის ფაქტორიალს რეკურსიული მეთოდით...
```

## Requirements

- **Python 3.9+** (standard library only, no pip dependencies)
- **macOS or Linux**
- **Claude Code** with hooks support

## Quick Install

### One-liner

```bash
git clone https://github.com/YOUR_USERNAME/claude-auto-translate.git && cd claude-auto-translate && ./install.sh
```

### Manual Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/claude-auto-translate.git
   cd claude-auto-translate
   ```

2. Run the installer:
   ```bash
   ./install.sh
   ```

3. Set your API key (choose one):
   ```bash
   # Option A: Environment variable (recommended)
   export ANTHROPIC_API_KEY='your-key-here'
   
   # Option B: Edit config file
   # Edit ~/.claude/skills/claude-auto-translate/config.json
   ```

4. Restart Claude Code to load the hook.

### Project-level Installation

To also install in your current project's `.claude/` directory:

```bash
./install.sh --project
```

## Configuration

Configuration is stored in `~/.claude/skills/claude-auto-translate/config.json`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable translation |
| `user_language` | string | `"Georgian"` | Your native language name |
| `working_language` | string | `"English"` | AI's working language |
| `display_mode` | string | `"native"` | `"native"` or `"bilingual"` |
| `provider` | string | `"anthropic"` | Translation provider to use |
| `timeout_seconds` | number | `10` | Global request timeout (seconds) |

**Note:** The hook is registered with a 15-second timeout (slightly above the default 10s request timeout). Very long prompts (over ~9,500 characters) are passed through without translation to stay within Claude Code's 10,000-character context limit.

### Provider Configuration

Each provider can be configured under the `providers` key:

```json
{
  "providers": {
    "anthropic": {
      "model": "claude-haiku-5-5",
      "timeout_seconds": 15
    },
    "openai": {
      "model": "gpt-4o-mini"
    },
    "gemini": {
      "model": "gemini-3.5-flash-lite"
    }
  }
}
```

### Environment Variables for API Keys

| Provider | Environment Variable |
|----------|---------------------|
| Anthropic (default) | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Google Gemini | `GEMINI_API_KEY` |
| DeepL | `DEEPL_API_KEY` |
| Google Cloud Translation | `GOOGLE_CLOUD_API_KEY` |

**Note:** Environment variables take precedence over config file keys.

### Supported Providers

| Provider | Type | Best For |
|----------|------|----------|
| `anthropic` | LLM | High quality, nuanced translations |
| `openai` | LLM | Good quality, fast |
| `gemini` | LLM | Good quality, generous free tier |
| `deepl` | MT | European languages, formal text |
| `google_cloud` | MT | Wide language support |

## Display Modes

### Native Mode (default)

Claude responds only in your native language. The English translation is injected as context that Claude sees but isn't displayed to you.

```json
{"display_mode": "native"}
```

### Bilingual Mode

In addition to the context for Claude, a `systemMessage` is shown to you in the transcript so you can verify the translation:

```json
{"display_mode": "bilingual"}
```

Example message shown to you:
```
[Translation: Please explain what this function does...]
```

Then Claude responds in your native language:
```
ეს ფუნქცია ითვლის ფაქტორიალს...
```

## Enable/Disable

### Via Environment Variable

```bash
# Disable temporarily
export CLAUDE_AUTO_TRANSLATE_ENABLED=false

# Re-enable
export CLAUDE_AUTO_TRANSLATE_ENABLED=true
```

### Via Config File

Edit `config.json`:
```json
{"enabled": false}
```

## What Gets Preserved (Not Translated)

The skill automatically preserves:

- Code blocks (` ``` ` and ` ~~~ `)
- Inline code (`` ` ``)
- URLs (`https://...`, `http://...`, `ftp://...`, `file://...`)
- File paths (`/path/to/file`, `./relative`, `~/home`, `C:\Windows`)
- Programming identifiers (`camelCase`, `snake_case`, `PascalCase`, `CONSTANT_CASE`)

## Troubleshooting

### Translation not working

1. **Check if enabled:**
   ```bash
   cat ~/.claude/skills/claude-auto-translate/config.json | grep enabled
   ```

2. **Verify API key is set:**
   ```bash
   echo $ANTHROPIC_API_KEY  # Should show your key (or be empty if using config)
   ```

3. **Check for errors in Claude Code output** — The skill writes warnings to stderr when something fails.

### Hook not loading

1. **Verify installation:**
   ```bash
   cat ~/.claude/settings.json | grep claude-auto-translate
   ```
   
   The hook should appear in a three-level nested structure:
   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         {
           "hooks": [
             {"type": "command", "command": "python3 ... || exit 0", "timeout": 15}
           ]
         }
       ]
     }
   }
   ```

2. **Restart Claude Code** — Hooks are loaded on startup.

### English prompts being translated

English/ASCII-only prompts should pass through unchanged. If they're being translated:

1. Check that the prompt doesn't contain non-ASCII characters
2. The detection threshold might need adjustment (open an issue if this happens consistently)

### Timeout errors

Increase the timeout in config:
```json
{
  "timeout_seconds": 20,
  "providers": {
    "anthropic": {
      "timeout_seconds": 25
    }
  }
}
```

## Uninstall

```bash
./uninstall.sh
```

To keep your config file (with API keys):
```bash
./uninstall.sh --keep-config
```

To also remove from project directory:
```bash
./uninstall.sh --project
```

## Privacy Note

**Your prompts are sent to the translation provider you configure.** 

- If using Anthropic/OpenAI/Gemini: prompts go to their LLM APIs
- If using DeepL/Google Cloud: prompts go to their translation APIs

Review your chosen provider's privacy policy. The skill only sends the text portions of your prompt (code blocks, URLs, and paths are extracted and not sent).

English-only or code-only prompts are **never** sent to any API.

---

## ქართულად (Georgian Section)

### რა არის ეს?

**Claude Auto-Translate** საშუალებას გაძლევთ გამოიყენოთ Claude Code ქართულ ენაზე. თქვენი prompt-ები ავტომატურად ითარგმნება ინგლისურად, ხოლო Claude გიპასუხებთ ქართულად.

### ინსტალაცია

```bash
git clone https://github.com/YOUR_USERNAME/claude-auto-translate.git
cd claude-auto-translate
./install.sh
```

შემდეგ დააყენეთ API გასაღები:
```bash
export ANTHROPIC_API_KEY='თქვენი-გასაღები'
```

გადატვირთეთ Claude Code.

### გამოყენება

უბრალოდ დაწერეთ თქვენი prompt-ი ქართულად:

```
გთხოვთ დამეხმარეთ ამ კოდის გამართვაში
```

Claude მიიღებს ინგლისურ თარგმანს და გიპასუხებთ ქართულად.

### კონფიგურაცია

შეცვალეთ `~/.claude/skills/claude-auto-translate/config.json`:

```json
{
  "enabled": true,
  "user_language": "Georgian",
  "display_mode": "native"
}
```

### დროებით გამორთვა

```bash
export CLAUDE_AUTO_TRANSLATE_ENABLED=false
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.

Copyright (c) 2026 Andro Lomtadze
