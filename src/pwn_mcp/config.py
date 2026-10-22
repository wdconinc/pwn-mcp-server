"""Runtime configuration: cache/output locations, offline mode, network timeouts."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_cache_dir

APP_NAME = "pwn-mcp"


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


OFFLINE: bool = _env_flag("PWN_MCP_OFFLINE")
"""When true, never contact remote services; only bundled data is used."""

TIMEOUT_S: float = float(os.environ.get("PWN_MCP_TIMEOUT", "30"))
"""Per-request timeout for remote services, in seconds."""

CACHE_DIR = Path(os.environ.get("PWN_MCP_CACHE_DIR", user_cache_dir(APP_NAME)))
OUTPUT_DIR = Path(os.environ.get("PWN_MCP_OUTPUT_DIR", CACHE_DIR / "output"))


def cache_dir(*parts: str) -> Path:
    path = CACHE_DIR.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR
