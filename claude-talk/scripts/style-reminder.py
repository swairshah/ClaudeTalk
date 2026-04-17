#!/usr/bin/env python3
"""
UserPromptSubmit hook: emits a one-line reminder of the current voice
style so style changes take effect on the next message without needing
a session restart. The full voice prompt was already injected at
SessionStart; this just nudges the verbosity dial.
"""

import json
import sys

STATE_FILE = "/tmp/loqui-tts-state.json"

REMINDERS = {
    "succinct": "(Voice style: SUCCINCT — keep <voice> tags brief, 1-2 sentences max, only the essentials.)",
    "verbose": "(Voice style: VERBOSE — use <voice> tags conversationally throughout your response.)",
    "chatty": "(Voice style: CHATTY — narrate intent before acting, react to findings out loud, use 3+ <voice> tags per turn.)",
}


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    # Read hook input but we don't need anything from it
    try:
        sys.stdin.read()
    except Exception:
        pass

    state = load_state()
    if not state.get("enabled", True):
        sys.exit(0)

    style = state.get("style", "verbose")
    reminder = REMINDERS.get(style)
    if not reminder:
        sys.exit(0)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reminder,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
