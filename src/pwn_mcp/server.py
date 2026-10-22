"""MCP server entry point: tools, resources and prompts for pulsar wind nebulae."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from mcp.server.mcpserver import MCPServer

from pwn_mcp import tools

try:
    __version__ = version("pwn-mcp-server")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0"

INSTRUCTIONS = """\
Query catalogs of pulsar wind nebulae (PWNe) and other nebulae (supernova remnants,
H II regions, planetary nebulae), render survey images (including the Canadian Galactic
Plane Survey), and compare nebular colours under the CIE 1931 2° and CIE 1964 10°
standard observers.
"""

mcp = MCPServer(name="pwn-mcp", version=__version__, instructions=INSTRUCTIONS)
tools.register_all(mcp)


@mcp.tool()
def server_info() -> dict:
    """Report the server version and which optional capabilities are enabled."""
    from pwn_mcp import config

    return {
        "name": "pwn-mcp",
        "version": __version__,
        "offline": config.OFFLINE,
        "cache_dir": str(config.CACHE_DIR),
        "output_dir": str(config.OUTPUT_DIR),
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
