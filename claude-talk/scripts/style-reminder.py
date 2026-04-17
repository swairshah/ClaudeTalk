#!/usr/bin/env python3
"""
UserPromptSubmit hook. Two jobs:

1. Drain stale speech from this session's queue. Without this, voice
   chunks from prior turns keep playing after the user has already
   moved on, so they hear "old" responses. Mirrors what the pi extension
   does on message_start.

2. Emit a one-line reminder of the current voice style so /tts-style
   takes effect immediately without a session restart.
"""

import json
import socket
import sys

STATE_FILE = "/tmp/loqui-tts-state.json"
TTS_HOST = "127.0.0.1"
BROKER_PORT = 18081

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


def stop_session_speech(session_id):
    """Fire-and-forget stop for this session's queued + playing speech."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((TTS_HOST, BROKER_PORT))
        cmd = {"type": "stop", "sourceApp": "claude-code", "sessionId": session_id}
        sock.sendall(json.dumps(cmd).encode() + b"\n")
        sock.close()
    except Exception:
        pass


def main():
    # Read hook input but we don't need anything from it
    try:
        sys.stdin.read()
    except Exception:
        pass

    state = load_state()
    if not state.get("enabled", True):
        sys.exit(0)

    # Drain any stale speech queued for this session before starting the new turn.
    session_id = state.get("session_id", "")
    if session_id:
        stop_session_speech(session_id)

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
