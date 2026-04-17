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
from datetime import datetime

STATE_FILE = "/tmp/loqui-tts-state.json"
DEBUG_LOG = "/tmp/loqui-tts-debug.log"
TTS_HOST = "127.0.0.1"
BROKER_PORT = 18081


def debug(msg):
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] reminder: {msg}\n")
    except Exception:
        pass

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
        # Read the broker's response so we know whether the stop took effect
        sock.settimeout(1)
        try:
            data = b""
            while b"\n" not in data:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                data += chunk
            debug(f"stop sent for sessionId={session_id!r}: response={data.decode().strip()!r}")
        except Exception as e:
            debug(f"stop sent for sessionId={session_id!r}: no response ({e})")
        sock.close()
    except Exception as e:
        debug(f"stop FAILED for sessionId={session_id!r}: {e}")


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
    debug(f"=== START === session_id={session_id!r} enabled={state.get('enabled', True)}")
    if session_id:
        stop_session_speech(session_id)
    else:
        debug("no session_id in state, skipping stop")

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
