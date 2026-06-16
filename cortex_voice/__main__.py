"""cortex-voice MCP server entry point.

An ears-only voice-capture MCP for Cortex. On macOS it records a short
utterance, transcribes it on-device with Apple's Speech framework, and returns
the transcript plus a routing intent ('recall' or 'remember'). It never reads
or writes Cortex itself — after ``listen``, the caller chains to the Cortex MCP
recall/remember tools as indicated by ``next_action``.

Run: ``python -m cortex_voice`` (stdio MCP transport).
"""

from __future__ import annotations

import signal
import sys

from fastmcp import FastMCP

from cortex_voice.server import mcp_tools

mcp = FastMCP(
    name="cortex-voice",
    version="1.0.0",
    instructions=(
        "Voice capture MCP for Cortex (macOS, on-device Apple Speech). Call "
        "check_voice_setup once to compile the helper and grant Microphone + "
        "Speech Recognition permissions. Call listen to record and transcribe a "
        "short spoken utterance; it returns the transcript and an intent "
        "('recall' or 'remember'). This server is ears-only: after listen, chain "
        "to the Cortex MCP recall or remember tool as indicated by next_action. "
        "It never reads or writes memories itself."
    ),
)

mcp_tools.register(mcp)


def _shutdown(sig=None, frame=None) -> None:
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
