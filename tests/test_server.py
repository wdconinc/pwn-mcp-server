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


def test_catalog_tools_offline():
    data = json.loads(call("search_nebulae", {"kind": "pwn", "in_cgps": True}).content[0].text)
    assert data["count"] >= 10
    rec = json.loads(call("get_nebula", {"name": "Kes 75"}).content[0].text)
    assert rec["pulsar"] == "J1846-0258" and rec["cgps"]["in_cgps"] is False
    cov = json.loads(call("cgps_coverage", {"l": 130.7, "b": 3.1}).content[0].text)
    assert cov["in_cgps"] is True


def test_live_tool_reports_offline():
    result = call("get_pulsar", {"name": "J9999+9999"})
    assert result.is_error


def test_resources_and_prompts():
    async def run():
        async with Client(mcp) as client:
            uris = {str(r.uri) for r in (await client.list_resources()).resources}
            csv = await client.read_resource("pwn://catalog/pwne")
            prompts = {p.name for p in (await client.list_prompts()).prompts}
            msg = await client.get_prompt("summarize_pwn", {"name": "Kes 75"})
            return uris, csv, prompts, msg

    uris, csv, prompts, msg = anyio.run(run)
    assert {"pwn://catalog/pwne", "pwn://surveys", "pwn://references", "pwn://lines"} <= uris
    assert "Crab Nebula" in csv.contents[0].text
    assert {"summarize_pwn", "compare_nebula_colors"} <= prompts
    assert "Kes 75" in msg.messages[0].content.text


def test_map_and_population_tools_offline():
    for name, args in (
        ("plot_galactic_map", {}),
        ("plot_galactic_map", {"projection": "allsky"}),
        ("plot_ppdot", {"include_atnf": False}),
        ("plot_population", {}),
    ):
        result = call(name, args)
        assert not result.is_error, result.content
        assert result.content[0].type == "image"
    # Live background requested while offline: still renders, with a note.
    note = json.loads(call("plot_ppdot", {"include_atnf": True}).content[1].text)["note"]
    assert note and "offline" in note.lower()


def test_startup_does_not_import_heavy_stacks():
    """Startup must stay well inside MCP client timeouts: colour, astropy coordinates/WCS,
    matplotlib and the remote-query clients load on the first tool call that needs them."""
    import subprocess
    import sys

    code = (
        "import sys, pwn_mcp.server\n"
        "heavy = ('colour', 'astropy.coordinates', 'astropy.wcs',\n"
        "         'matplotlib.pyplot', 'astroquery', 'psrqpy')\n"
        "print(','.join(m for m in heavy if m in sys.modules))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == ""
