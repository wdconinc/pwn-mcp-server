# pwn-nebulae plugin

Adds the [pwn-mcp-server](https://github.com/wdconinc/pwn-mcp-server) MCP server to Claude Code:
catalogs of pulsar wind nebulae and other nebulae, Canadian Galactic Plane Survey (CGPS) and
multi-wavelength survey images, Galactic maps, P–Ṗ and population plots, and nebular colours under
the CIE 1931 2° and CIE 1964 10° standard observers.

## Requirements

[uv](https://docs.astral.sh/uv/getting-started/installation/) on your `PATH`. The server runs locally
with `uvx` from the `main` branch on GitHub, so each start picks up the latest version. The first
start downloads the dependencies (a minute or so); later starts take a few seconds.

Network access is needed for SIMBAD, VizieR, ATNF, CADC and image surveys. Results are cached
under your user cache directory, and the bundled catalog works offline.

## Try it

- "Which pulsar wind nebulae lie in the CGPS footprint?"
- "Show DA 495 in CGPS 1420 MHz."
- "Compare 3C 58 in radio, optical, infrared and X-rays."
- "How does a planetary nebula's colour differ between the 2° and 10° observers?"

The server also offers the prompts `summarize_pwn` and `compare_nebula_colors`.
