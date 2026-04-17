# ClaudeTalk

Make [Claude Code](https://docs.anthropic.com/en/docs/claude-code) talk to you. ClaudeTalk gives Claude a voice — it speaks summaries, explanations, and questions out loud while you work, so you can keep your eyes on what matters.

## Install

You need two things: the **PiTalk** macOS app (the thing that actually plays audio) and the **ClaudeTalk** plugin (the thing that talks to it).

```bash
brew install swairshah/tap/pitalk
open -a PiTalk
```

Then in Claude Code:

```
/plugin marketplace add swairshah/ClaudeTalk
/plugin install claude-talk@claudetalk
```

Restart Claude Code and you're done. The next response should speak.

## Using it

ClaudeTalk works automatically — Claude wraps spoken parts of its responses in `<voice>` tags, ClaudeTalk pulls them out and sends them to PiTalk. The terminal still shows clean text; only the spoken parts get audio.

| Command | What it does |
|---------|--------------|
| `/claude-talk:tts` | Turn TTS on or off |
| `/claude-talk:tts-stop` | Stop the current speech |
| `/claude-talk:tts-say <text>` | Say arbitrary text |
| `/claude-talk:tts-voice [name]` | Pick a voice (defaults to auto) |
| `/claude-talk:tts-style [mode]` | How chatty Claude should be: `succinct`, `verbose`, or `chatty` |
| `/claude-talk:tts-status` | Check what's running |

Voices: `auto`, `alba`, `marius`, `javert`, `fantine`, `cosette`, `eponine`, `azelma`.

**Stop speech anywhere on macOS:** press **Cmd+.** — works from any app, not just Claude Code.

## About PiTalk

[PiTalk](https://github.com/swairshah/pi-talk-app) is the menu bar app that handles audio. ElevenLabs voices, per-session queueing, automatic pause when your mic is active, and a global stop hotkey. Install it once, and any agent that knows the protocol (ClaudeTalk, [Pi](https://github.com/mariozechner/pi-coding-agent), and others) can use it.

## License

MIT. Plugin internals: [`scripts/`](claude-talk/scripts/), [`hooks/hooks.json`](claude-talk/hooks/hooks.json).
