# ClaudeTalk

Text-to-speech plugin for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Speaks `<voice>` tagged content from Claude's responses through the [PiTalk](https://github.com/swairshah/pi-talk-app) macOS app.

## Requirements

ClaudeTalk needs the **PiTalk** macOS menu bar app running — that's the broker that actually plays audio.

```bash
brew install swairshah/tap/pitalk
open -a PiTalk
```

## Installation

```
/plugin marketplace add swairshah/ClaudeTalk
/plugin install claude-talk@claudetalk
```

That's it. New Claude Code sessions will start using `<voice>` tags in their responses, and PiTalk will speak the tagged content.

## How it works

1. **SessionStart hook** injects a system prompt teaching Claude to wrap conversational content in `<voice>` tags
2. **Stop hook** runs after each response, extracts `<voice>` content from the assistant's last message, sends it to the PiTalk broker over TCP
3. **PiTalk** (separate macOS app) plays the audio via ElevenLabs

The terminal renders Claude's response with the `<voice>` tags stripped, so visually it looks normal — only the audio side cares about the markers.

### Limitation

Claude Code's hook system only fires after a full response completes (no streaming-delta hook). So speech plays *after* the response, not during streaming. The Pi coding agent extension equivalent does support real-time streaming because it has a `message_update` hook.

## Commands

| Command | Description |
|---------|-------------|
| `/claude-talk:tts` | Toggle TTS on/off |
| `/claude-talk:tts-stop` | Stop current speech |
| `/claude-talk:tts-say <text>` | Speak arbitrary text |
| `/claude-talk:tts-voice [name]` | Change/show voice |
| `/claude-talk:tts-status` | Show TTS status |

### Available voices

`auto` (default), `alba`, `marius`, `javert`, `fantine`, `cosette`, `eponine`, `azelma`

## Architecture

```
ClaudeTalk/
├── .claude-plugin/
│   ├── plugin.json              # Plugin manifest
│   └── marketplace.json         # Marketplace listing
├── hooks/
│   └── hooks.json               # SessionStart + Stop + SessionEnd hooks
├── scripts/
│   ├── session-start.py         # Injects voice prompt, checks broker health
│   ├── speak-response.py        # Extracts <voice> tags from assistant message, sends to broker
│   ├── session-end.py           # Cleanup
│   ├── inbox-watcher.sh         # Watches for voice input from external apps
│   └── tts-control.py           # CLI for stop/say/toggle/voice/status
├── commands/                    # Slash command definitions
└── skills/                      # Background skill for voice awareness
```

### State

State is persisted to `/tmp/loqui-tts-state.json` (enabled, voice, session ID, broker health, Claude PID).

### Broker protocol

NDJSON over TCP on port 18081:

- `{"type": "speak", "text": "...", "sourceApp": "claude-code", "sessionId": "..."}`
- `{"type": "stop"}`
- `{"type": "health"}`

## License

MIT
