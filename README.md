# cortex-voice

On-device **voice capture MCP for Cortex** (macOS). Speak; it records a short
utterance, transcribes it locally with Apple's Speech framework, decides whether
you asked a question or stated a fact, and hands back the transcript plus a
routing hint. It is **ears-only** — it never reads or writes memories itself.
The caller chains to the **Cortex MCP** `recall`/`remember` tools.

```
you: "remember that the cortex-viz MCP times out on first-run dep install"
Claude → listen()                     # cortex-voice records + transcribes
  ← { transcript, intent: "remember", suggested_tags: [...], next_action }
Claude → cortex remember(content=transcript, tags=[...,"voice"])   # Cortex MCP
```

## Why ears-only

Cortex owns the memory pipeline (embeddings, heat, predictive-coding write gate,
WRRF retrieval). Re-implementing any of that here would duplicate and inevitably
diverge from the single source of truth. So cortex-voice does exactly one thing —
turn speech into text + an intent — and lets Cortex's own tools do the memory
work. Voice = ears, Cortex = memory, Claude = orchestrator.

## Tools

| Tool | Purpose |
|---|---|
| `check_voice_setup()` | Compile the native helper and report Microphone + Speech Recognition authorization. **Call once before first use** to trigger the macOS permission prompts. |
| `listen(mode="auto", max_seconds=15, silence_ms=1200, locale=None)` | Record + transcribe one utterance. Returns `{transcript, intent, suggested_tags, confidence, duration_s, on_device, next_action}`. `mode`: `auto` (classify), `recall`, or `remember`. |

## How it works

- A small Swift helper (`scripts/voicecap.swift`) does mic capture
  (`AVAudioEngine`) + recognition (`SFSpeechRecognizer`, on-device when
  supported), with silence-based endpointing. It emits one JSON line.
- The helper is **compiled lazily** with `swiftc` on first use into the plugin's
  persistent `deps/bin/` dir, carrying an embedded `Info.plist` so the macOS
  permission prompts read sensibly. Compilation is deferred so the MCP handshake
  stays instant (no startup-timeout risk).
- The Python FastMCP server (`cortex_voice/`) subprocesses the helper off the
  event loop, classifies intent deterministically (`voice/intent.py`), and
  returns the structured result.

## Requirements

- **macOS** (Apple Speech framework) with the Xcode command-line tools / Swift
  toolchain (`swiftc`).
- Microphone + Speech Recognition permission granted to the controlling app
  (your terminal or the Claude app) in *System Settings → Privacy & Security*.
- On-device recognition downloads a per-locale model once (OS-managed).

## Configuration

`userConfig` in `plugin.json`: `locale` (default `en-US`) and `default_mode`
(default `auto`). These map to the `VOICE_LOCALE` / `VOICE_DEFAULT_MODE` env vars
the server reads.

## License

MIT.
