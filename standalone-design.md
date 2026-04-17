# Standalone ClaudeTalk Design Notes

Goal: ship ClaudeTalk so users don't need to install PiTalk separately. The plugin should be self-contained — `/plugin install` and they can hear Claude speak.

## What PiTalk currently provides

1. TCP broker on port 18081 (NDJSON: `speak`, `stop`, `health`)
2. HTTP health endpoint on port 18080
3. ElevenLabs streaming → MP3 → `ffplay` playback
4. Per-source queue management (round-robin between sessions)
5. Microphone activity monitor (interrupts speech when mic active)
6. Global Cmd+. hotkey to stop speech
7. Menu bar UI: settings, sessions, history, voice picker
8. ElevenLabs API key storage (UserDefaults)

## Three options

### Option A: Bundle PiTalk as a headless binary

Strip the SwiftUI views from PiTalk, ship a `claudetalk-brokerd` binary inside the plugin. Plugin auto-launches it on session start, kills on session end (or leaves running across sessions).

- ✅ Reuses 100% of working Swift code (queues, mic monitor, hotkey)
- ❌ Need to code-sign + notarize a Swift binary for distribution
- ❌ macOS-only, ~10MB ship weight per release
- ❌ Plugin repo grows large; need release-tag + binary upload workflow

### Option B: Rewrite broker in Python, bundled in `scripts/`

Pure `broker.py` that does TCP listen + TTS provider call + audio playback. Spawned as daemon on session start via existing inbox-watcher pattern.

- ✅ Zero binary install, ships as plain text
- ✅ Potentially cross-platform (Linux Claude Code support)
- ❌ Rewrite working code
- ❌ Lose mic monitoring + global hotkey unless we re-add them

### Option C (recommended): Hybrid — Python broker with smart fallback

Same as B, but: default to macOS built-in `say` + `afplay` (zero deps). Upgrade to ElevenLabs streaming if user provides an API key via `/tts-config <key>`. Drop mic monitoring + hotkey; rely on `/tts-stop` slash command for interruption.

- ✅ True one-command install, no brew, no .app bundle
- ✅ Works out of the box with no API keys
- ✅ Cross-platform potential (Linux can use `espeak` or skip audio)
- ❌ `say` voices sound robotic vs ElevenLabs
- ❌ Lose the nice PiTalk niceties (mic interrupt, Cmd+., history UI)

**Positioning:** PiTalk becomes the premium experience for users who want the menubar UI, history, mic monitoring, and use TTS across multiple agents. ClaudeTalk standalone is the friction-free entry point — installs in one command, speaks immediately.

## Sketch for Option C

```
ClaudeTalk/
├── scripts/
│   ├── broker.py             # NEW: TCP broker daemon
│   ├── tts_providers.py      # NEW: SayProvider, ElevenLabsProvider
│   ├── session-start.py      # MODIFIED: spawn broker if not running
│   ├── speak-response.py     # NO CHANGE — same broker protocol
│   ├── session-end.py
│   └── tts-control.py        # ADD: /tts-config command for API key
└── ...
```

`broker.py`:
- Bind 18081, listen for NDJSON commands
- Single worker thread with a queue
- For each `speak`: call active provider, stream audio to subprocess, track PID
- For `stop`: kill current playback subprocess, drain queue
- Lifecycle: spawn detached on first session-start, persist across sessions, health-check before respawn
- PID file: `/tmp/claudetalk-broker.pid`

State file: `~/.claudetalk/config.json` (provider, API key, voice)

## Open questions

- Stop hotkey without a UI app? Could ship a tiny launchd-managed Swift helper just for the hotkey, or skip it entirely and rely on the slash command.
- Mic interruption — can be done from a Python daemon via PyObjC or a small CGEventTap shim, but adds complexity. Defer.
- Linux support — Claude Code runs on Linux. Standalone broker could use `espeak-ng` or just degrade gracefully (queue speech, do nothing). Worth scoping.
- Migration path for existing PiTalk users — should the plugin defer to a running PiTalk if it detects one (port 18081 already bound)? Probably yes, fall back to standalone broker only if PiTalk isn't there.
