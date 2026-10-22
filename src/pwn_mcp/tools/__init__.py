"""MCP tool groups. Each module exposes ``register(mcp)``."""

from __future__ import annotations

from mcp.server.mcpserver import Image

from ..plotting import save_figure


def figure_result(fig, stem: str, data: dict | None = None) -> list:
    """Standard image-tool result: the PNG plus a JSON block with metadata and the saved path."""
    png, path = save_figure(fig, stem)
    return [Image(data=png, format="png"), {"saved_to": str(path), **(data or {})}]


def register_all(mcp) -> None:
    from . import color

    color.register(mcp)
