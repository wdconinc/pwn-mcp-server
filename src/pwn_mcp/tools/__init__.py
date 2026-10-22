"""MCP tool groups. Each module exposes ``register(mcp)``."""

from __future__ import annotations

import functools
import logging

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from ..plotting import save_figure

log = logging.getLogger("pwn_mcp")


def tool(mcp: MCPServer, **kwargs):
    """Register a tool whose failures reach the model as readable ``ToolError`` messages.

    MCPServer reports any other exception as an opaque crash; here an unknown name, a position
    outside a survey or an unreachable remote service are expected outcomes the model can act on.
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kw):
            try:
                return fn(*args, **kw)
            except ToolError:
                raise
            except (ValueError, LookupError) as exc:
                raise ToolError(str(exc)) from exc
            except Exception as exc:
                log.warning("tool %s failed", fn.__name__, exc_info=True)
                raise ToolError(f"{type(exc).__name__}: {exc}") from exc

        mcp.tool(**kwargs)(wrapper)
        return fn

    return decorator


def figure_result(fig, stem: str, data: dict | None = None) -> list:
    """Standard image-tool result: the PNG plus a JSON block with metadata and the saved path."""
    png, path = save_figure(fig, stem)
    return [Image(data=png, format="png"), {"saved_to": str(path), **(data or {})}]


def register_all(mcp: MCPServer) -> None:
    from . import catalog, color, imaging, live

    catalog.register(mcp)
    live.register(mcp)
    color.register(mcp)
    imaging.register(mcp)
