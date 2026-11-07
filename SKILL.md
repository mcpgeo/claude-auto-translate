---
name: claude-auto-translate
description: Automatically translates non-English user prompts to English for Claude, with instructions to respond in the user's native language
version: 0.1.0
author: Andro Lomtadze
hooks:
  - UserPromptSubmit
---

# Claude Auto-Translate Skill

This skill enables users to interact with Claude Code in their native language while maintaining high-quality AI responses.

## What This Skill Does

When a user writes a prompt in a non-English language (e.g., Georgian), this skill:

1. **Detects** that the prompt contains non-English text
2. **Preserves** code blocks, URLs, file paths, and identifiers (they are not translated)
3. **Translates** the natural language portions to English using a configured translation provider
4. **Injects context** via `additionalContext` that tells Claude:
   - The original prompt was in the user's native language
   - The English translation of what the user asked
   - An instruction to respond in the user's native language

## How Claude Should Handle Translations

When you receive context from this skill indicating a translation:

1. **Use the English translation** to understand what the user is asking
2. **Respond entirely in the user's native language** as specified
3. **Keep code, file paths, and technical terms** in their original form (usually English)
4. **Do not mention** that translation occurred unless the user asks about it

## Display Modes

- **Native mode** (default): Context is injected for Claude but nothing is shown to the user
- **Bilingual mode**: A `systemMessage` is also shown to the user with the English translation, so they can verify it

## Configuration

The skill is configured via `config.json` in the skill directory. Key settings:

- `user_language`: The user's native language (default: "Georgian")
- `working_language`: The AI's working language (default: "English")  
- `display_mode`: Either "native" or "bilingual"
- `provider`: Translation service to use (anthropic, openai, gemini, deepl, google_cloud)
- `timeout_seconds`: Request timeout (default: 10 seconds)

## Limits

- Context strings are capped at 10,000 characters per Claude Code docs
- Very long prompts (over ~9,500 chars) are passed through without translation
- The hook never blocks prompts (always exits 0)

## Privacy Note

User prompts that require translation are sent to the configured translation provider's API. Users should review the privacy policies of their chosen provider.
