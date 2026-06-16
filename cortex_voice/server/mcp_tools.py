"""MCP tool registration for the cortex-voice server.

Two tools, both ears-only:
  * listen            — record + transcribe a short utterance, classify intent.
  * check_voice_setup — compile the helper and report mic/speech authorization.

Neither tool touches Cortex. ``listen`` returns a ``next_action`` telling the
caller which Cortex MCP tool to chain to (recall or remember).
"""

from __future__ import annotations

import asyncio
import os

from fastmcp import FastMCP

from cortex_voice.voice import helper, intent

_VALID_MODES = ("auto", "recall", "remember")


def _default_locale() -> str:
    return os.environ.get("VOICE_LOCALE") or "en-US"


def _default_mode() -> str:
    mode = os.environ.get("VOICE_DEFAULT_MODE", "auto")
    return mode if mode in _VALID_MODES else "auto"


def register(mcp: FastMCP) -> None:
    """Register cortex-voice tools on the FastMCP instance."""
    _register_listen(mcp)
    _register_check_setup(mcp)


def _next_action(resolved: str) -> str:
    if resolved == "recall":
        return "Call the Cortex MCP recall tool with query=transcript."
    return (
        "Call the Cortex MCP remember tool with content=transcript and "
        "tags=suggested_tags + ['voice']."
    )


def _register_listen(mcp: FastMCP) -> None:
    @mcp.tool(
        name="listen",
        description=(
            "Record a short spoken utterance from the microphone, transcribe it "
            "on-device (Apple Speech), and classify it as a recall query or a "
            "memory to remember. Returns the transcript plus a routing hint. This "
            "tool does NOT touch Cortex: after calling it, chain to the Cortex "
            "MCP per next_action — intent 'recall' -> cortex recall(query); "
            "intent 'remember' -> cortex remember(content, tags). mode 'auto' "
            "lets the classifier decide; 'recall'/'remember' force the routing."
        ),
    )
    async def tool_listen(
        mode: str = "auto",
        max_seconds: float = 15.0,
        silence_ms: float = 1200.0,
        locale: str | None = None,
    ) -> dict:
        if mode not in _VALID_MODES:
            mode = _default_mode()
        loc = locale or _default_locale()
        try:
            result = await asyncio.to_thread(
                helper.capture, max_seconds, silence_ms, loc
            )
        except helper.VoiceHelperError as exc:
            return {
                "ok": False,
                "error": str(exc),
                "hint": (
                    "Run check_voice_setup to compile the helper and grant "
                    "Microphone + Speech Recognition permissions."
                ),
            }
        transcript = (result.get("transcript") or "").strip()
        if not transcript:
            return {
                "ok": False,
                "error": "no speech detected",
                "duration_s": result.get("duration"),
            }
        resolved = intent.classify(transcript) if mode == "auto" else mode
        return {
            "ok": True,
            "transcript": transcript,
            "intent": resolved,
            "suggested_tags": intent.suggest_tags(transcript),
            "confidence": result.get("confidence"),
            "duration_s": result.get("duration"),
            "on_device": result.get("on_device"),
            "next_action": _next_action(resolved),
        }


def _register_check_setup(mcp: FastMCP) -> None:
    @mcp.tool(
        name="check_voice_setup",
        description=(
            "Verify the cortex-voice capture helper: compile it if needed and "
            "report Microphone + Speech Recognition authorization. Call this once "
            "before first use to trigger the macOS permission prompts."
        ),
    )
    async def tool_check_voice_setup() -> dict:
        try:
            binary = await asyncio.to_thread(helper.ensure_binary)
        except helper.VoiceHelperError as exc:
            return {"ok": False, "error": str(exc)}
        try:
            auth = await asyncio.to_thread(helper.check_auth)
        except helper.VoiceHelperError as exc:
            return {"ok": False, "binary": str(binary), "error": str(exc)}
        ready = (
            auth.get("speech_auth") == "authorized"
            and auth.get("mic_auth") == "authorized"
        )
        hint = (
            None
            if ready
            else (
                "Grant Microphone and Speech Recognition to your terminal/Claude "
                "app in System Settings > Privacy & Security, then retry."
            )
        )
        return {"ok": ready, "binary": str(binary), "hint": hint, **auth}
