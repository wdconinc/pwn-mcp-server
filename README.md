# pwn-mcp-server

An [MCP](https://modelcontextprotocol.io) server for **pulsar wind nebulae** (PWNe) and other
nebulae. It can:

- query catalogs: a bundled curated PWN table, plus live SIMBAD, VizieR (Green SNR catalogue,
  H.E.S.S. HGPS, Sharpless, WISE H II, Strasbourg-ESO PNe), the ATNF pulsar catalogue and CADC
- render survey images, including the **Canadian Galactic Plane Survey** (CGPS)
- compare nebular colours under the **CIE 1931 2°** and **CIE 1964 10°** standard observers

> Work in progress; see the commit history for the current state.

## Quick start

```bash
uv sync
uv run pwn-mcp            # stdio MCP server
```

Register with Claude Code:

```bash
claude mcp add pwn -- uv run --directory /path/to/pwn-mcp-server pwn-mcp
```

Or run the container:

```bash
docker run -i --rm ghcr.io/wdconinc/pwn-mcp-server
```

## Development

```bash
uv run ruff check .
uv run pytest              # offline unit tests
uv run pytest -m network   # tests that contact remote services
```
