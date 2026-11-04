"""Import-level checks that hold on every platform.

The capture helper (scripts/voicecap.swift) needs macOS and user-granted permissions; the
Pipeline's `helper` job builds it there. These tests only prove the Python package
installs and wires its two tools, which is what the Linux `unit` job can measure.
"""

from __future__ import annotations

import asyncio
import importlib
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_package_modules_import() -> None:
    for name in (
        "cortex_voice",
        "cortex_voice.server.mcp_tools",
        "cortex_voice.voice.helper",
        "cortex_voice.voice.intent",
    ):
        importlib.import_module(name)


def test_register_declares_the_two_eyes_only_tools() -> None:
    from fastmcp import FastMCP

    from cortex_voice.server import mcp_tools

    mcp = FastMCP("cortex-voice-test")
    mcp_tools.register(mcp)
    # fastmcp >= 2: list_tools() is the public, async listing (verified on 4.1.6).
    names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    assert names == {"listen", "check_voice_setup"}, names


def test_declared_entry_point_resolves() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    target = project["scripts"]["cortex-voice"]
    module_name, attribute = target.split(":")
    assert callable(getattr(importlib.import_module(module_name), attribute))
