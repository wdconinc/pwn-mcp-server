import json

import anyio
from mcp import Client

from pwn_mcp.server import mcp


def call(name, args=None):
    async def run():
        async with Client(mcp) as client:
            return await client.call_tool(name, args or {})

    return anyio.run(run)


def test_server_lists_tools():
    async def run():
        async with Client(mcp) as client:
            return {t.name for t in (await client.list_tools()).tools}

    names = anyio.run(run)
    assert {"server_info", "nebula_color", "render_color_swatches"} <= names


def test_nebula_color_tool():
    result = call("nebula_color", {"template": "planetary_nebula"})
    assert not result.is_error
    data = json.loads(result.content[0].text)
    assert [o["observer"] for o in data["observers"]] == ["cie1931_2", "cie1964_10"]
    assert data["differences"][0]["delta_E2000"] > 0


def test_custom_lines_tool():
    result = call("nebula_color", {"lines": {"H_alpha": 3, "OIII_5007": 1}})
    assert not result.is_error


def test_image_tools_return_png_and_metadata():
    for name in ("render_color_swatches", "plot_chromaticity_comparison", "plot_cmf_comparison"):
        result = call(name)
        assert not result.is_error, result.content
        assert result.content[0].type == "image"
        assert result.content[0].mime_type == "image/png"
        assert "saved_to" in json.loads(result.content[1].text)
