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
4. **Injects context** that tells Claude:
   - The original prompt was in the user's native language
   - The English translation of what the user asked
   - An instruction to respond in the user's native language

## How Claude Should Handle Translations

When you receive a `[Translation Context]` block from this skill:

1. **Use the English translation** to understand what the user is asking
2. **Respond entirely in the user's native language** as specified
3. **Keep code, file paths, and technical terms** in their original form (usually English)
4. **Do not mention** that translation occurred unless the user asks about it
5. In **bilingual mode**, include a brief translation acknowledgment at the start of your response

## Configuration

The skill is configured via `config.json` in the skill directory. Key settings:

- `user_language`: The user's native language (default: "Georgian")
- `working_language`: The AI's working language (default: "English")  
- `display_mode`: Either "native" (respond only in user's language) or "bilingual" (show translation confirmation)
- `provider`: Translation service to use (anthropic, openai, gemini, deepl, google_cloud)

## Privacy Note

User prompts that require translation are sent to the configured translation provider's API. Users should review the privacy policies of their chosen provider.
