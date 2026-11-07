#!/usr/bin/env python3
"""
Claude Code UserPromptSubmit hook for claude-auto-translate.

This hook intercepts user prompts, detects non-English text,
translates it to English, and injects translation context for Claude.

Exit codes:
  0 - Success (translation injected or passthrough)
  
On any error, the hook exits 0 to never block the user's prompt.
"""

import json
import os
import sys

# Add the src directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from src.translate import process_prompt, warn


def main() -> int:
    """Main hook entry point."""
    try:
        # Read hook input from stdin
        input_data = sys.stdin.read()
        
        if not input_data:
            return 0
        
        try:
            hook_input = json.loads(input_data)
        except json.JSONDecodeError:
            warn("Invalid JSON input from Claude Code")
            return 0
        
        # Extract the user's prompt
        prompt = hook_input.get("prompt", "")
        
        if not prompt:
            return 0
        
        # Process the prompt (translate if needed)
        result = process_prompt(prompt)
        
        if result:
            # Output hook result as JSON
            # Using "continue" with additional context
            output = {
                "result": "continue",
                "context": result
            }
            print(json.dumps(output))
        
        return 0
    
    except Exception as e:
        warn(f"Hook error: {e}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
