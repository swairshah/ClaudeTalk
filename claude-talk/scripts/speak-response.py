#!/usr/bin/env python3
"""
Stop hook: Reads the transcript, extracts <voice> tags from the last assistant
message, and sends them to the Loqui broker for TTS playback.
"""

import json
import os
import re
import socket
import sys
import time
from datetime import datetime

TTS_HOST = "127.0.0.1"
BROKER_PORT = 18081
STATE_FILE = "/tmp/loqui-tts-state.json"
DEBUG_LOG = "/tmp/loqui-tts-debug.log"

# Per-message dedup. Shared with flush-voice.py (PreToolUse hook) so we don't
# re-speak chunks that already played mid-turn. Format: {msg_uuid: chunks_spoken}.
FLUSH_FILE = "/tmp/loqui-tts-flushed.json"


def debug(msg):
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")
    except:
        pass


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"enabled": True, "voice": "auto"}


def load_flushed():
    """Return {msg_uuid: chunk_count_already_spoken}."""
    try:
        with open(FLUSH_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_flushed(d):
    try:
        with open(FLUSH_FILE, "w") as f:
            json.dump(d, f)
    except Exception:
        pass


def send_to_broker(text, voice="auto", session_id="unknown", pid=None):
    """Send a speak command to the Loqui broker via TCP/NDJSON."""
    try:
        command = {
            "type": "speak",
            "text": text,
            "sourceApp": "claude-code",
            "sessionId": session_id,
        }
        if voice and voice != "auto":
            command["voice"] = voice
        if pid:
            command["pid"] = pid

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((TTS_HOST, BROKER_PORT))
        sock.sendall(json.dumps(command).encode() + b"\n")

        # Read response
        data = b""
        while b"\n" not in data:
            chunk = sock.recv(1024)
            if not chunk:
                break
            data += chunk
        sock.close()

        resp = json.loads(data.decode().strip())
        return resp.get("ok", False)
    except Exception:
        return False


def extract_voice_tags(text):
    """Extract all <voice>...</voice> content from text."""
    pattern = re.compile(r"<voice>(.*?)</voice>", re.DOTALL)
    matches = pattern.findall(text)
    # Strip any accidental nested markup
    cleaned = []
    for m in matches:
        clean = re.sub(r"<[^>]+>", " ", m).strip()
        clean = re.sub(r"\s+", " ", clean)
        if clean:
            cleaned.append(clean)
    return cleaned


def get_last_assistant_messages(transcript_path):
    """Read the transcript and get the last assistant message(s)."""
    if not transcript_path or not os.path.exists(transcript_path):
        return []

    messages = []
    try:
        with open(transcript_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("type") == "assistant":
                        messages.append(obj)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []

    return messages


def main():
    debug("=== speak-response.py START ===")

    # Read hook input
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        input_data = {}

    debug(f"input keys: {list(input_data.keys())}")

    state = load_state()

    # Check if TTS is enabled
    if not state.get("enabled", True):
        debug("TTS disabled, exiting")
        sys.exit(0)

    # Skip stop-hook continuations to avoid duplicate speech
    if input_data.get("stop_hook_active"):
        debug("stop_hook_active=True, skipping")
        sys.exit(0)

    session_id = state.get("session_id", input_data.get("session_id", "unknown"))
    voice = state.get("voice", "auto")
    pid = state.get("claude_pid", os.getpid())
    transcript_path = input_data.get("transcript_path", "")

    # Try to read the latest assistant message from the transcript — this gives
    # us a UUID we can use to dedup against chunks already flushed mid-turn by
    # the PreToolUse hook. Retry briefly because Claude Code flushes after Stop.
    msg_uuid = ""
    full_text = ""
    for attempt in range(8):
        messages = get_last_assistant_messages(transcript_path)
        if messages:
            last = messages[-1]
            msg_uuid = last.get("uuid", "")
            content = last.get("message", {}).get("content", "")
            if isinstance(content, list):
                full_text = " ".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            elif isinstance(content, str):
                full_text = content
            if full_text:
                debug(f"transcript msg {msg_uuid[:8]} ({len(full_text)} chars) on attempt {attempt}")
                break
        time.sleep(0.15 if attempt < 3 else 0.3)

    # Fallback: if transcript read failed, use last_assistant_message but skip
    # dedup (we have no UUID to key on). Risk is re-speaking a chunk that the
    # PreToolUse hook already flushed — accept that as the safer failure mode.
    if not full_text:
        last_msg = input_data.get("last_assistant_message")
        if isinstance(last_msg, str) and last_msg.strip():
            full_text = last_msg
            debug(f"transcript empty; using last_assistant_message ({len(full_text)} chars)")
        elif isinstance(last_msg, dict):
            content = last_msg.get("content") or last_msg.get("message", {}).get("content", "")
            if isinstance(content, list):
                full_text = " ".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            elif isinstance(content, str):
                full_text = content

    if not full_text:
        debug("no text to speak")
        sys.exit(0)

    chunks = extract_voice_tags(full_text)
    flushed = load_flushed()
    already = flushed.get(msg_uuid, 0) if msg_uuid else 0
    new_chunks = chunks[already:]

    debug(f"total={len(chunks)} flushed={already} new={len(new_chunks)}")

    for chunk in new_chunks:
        ok = send_to_broker(chunk, voice=voice, session_id=session_id, pid=pid)
        debug(f"  sent '{chunk[:60]}' ok={ok}")

    if msg_uuid:
        flushed[msg_uuid] = len(chunks)
        save_flushed(flushed)

    print(json.dumps({"spoken": len(new_chunks)}))
    sys.exit(0)


if __name__ == "__main__":
    main()
