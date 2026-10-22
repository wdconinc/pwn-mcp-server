# pwn-mcp-server

[![CI](https://github.com/wdconinc/pwn-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/wdconinc/pwn-mcp-server/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pwn-mcp-server)](https://pypi.org/project/pwn-mcp-server/)

An [MCP](https://modelcontextprotocol.io) server for **pulsar wind nebulae** (PWNe) and other
nebulae. It lets an LLM client:

- **query catalogs**: a bundled table of 37 well-studied PWNe and 16 showcase SNRs, H II regions
  and planetary nebulae, plus live SIMBAD, VizieR (Green's SNR catalogue, H.E.S.S. HGPS,
  Sharpless, WISE H II, Strasbourg-ESO PNe), the ATNF pulsar catalogue and CADC
- **render images**: survey cutouts with pulsar, SNR and PWN overlays, including native-resolution
  **Canadian Galactic Plane Survey** (CGPS) 1420 and 408 MHz mosaics from CADC, multi-wavelength
  panels, Galactic maps with the CGPS footprint, P–Ṗ and population plots
- **compare colour spaces**: the perceived colour of nebular spectra under the **CIE 1931 2°**
  and **CIE 1964 10°** standard observers (xy, u′v′, CIELAB, sRGB, ΔE2000, dominant wavelength),
  with reddening and the scotopic (rod) response

## Install and run

From PyPI with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from pwn-mcp-server pwn-mcp
```

Register it with Claude Code:

```bash
claude mcp add pwn -- uvx --from pwn-mcp-server pwn-mcp
```

Or run the container (stdio):

```bash
docker run -i --rm -v pwn-mcp-data:/data ghcr.io/wdconinc/pwn-mcp-server
```

Or from a checkout:

```bash
uv sync
uv run pwn-mcp
```

To inspect the tools interactively:

```bash
npx @modelcontextprotocol/inspector uvx --from pwn-mcp-server pwn-mcp
```

### Claude Code plugin

[`claude-plugin/`](claude-plugin/) packages the server as the `pwn-nebulae` Claude Code plugin,
which runs it with `uvx` from the `main` branch. To try it from a checkout:

```bash
claude --plugin-dir ./claude-plugin
```

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `PWN_MCP_OFFLINE` | unset | `1` disables all remote queries; only bundled data and cached results are used |
| `PWN_MCP_TIMEOUT` | `30` | Timeout for remote services (s) |
| `PWN_MCP_CACHE_DIR` | platform user cache dir | Cache for live queries and image cutouts (30-day TTL) |
| `PWN_MCP_OUTPUT_DIR` | `$PWN_MCP_CACHE_DIR/output` | Where rendered PNGs are saved |

## Tools

**Catalogs**

| Tool | What it does |
|---|---|
| `search_nebulae` | Filter the bundled catalog by name, kind, PWN class, Galactic position, CGPS coverage, pulsar Ė |
| `get_nebula` | Full record: position, host SNR (Green), pulsar (ATNF), TeV counterpart (HGPS), CGPS coverage; `live=true` adds SIMBAD/VizieR/ATNF/CADC detail |
| `cone_search` | Objects around a name or position in the bundled table, Green, HGPS, Sharpless, WISE H II, PNe, ATNF |
| `query_vizier` | Whole-catalog queries with constraints, e.g. all type-F (filled-centre) remnants in Green |
| `get_pulsar` | ATNF parameters for one pulsar |
| `cgps_coverage` | Whether a position is in the CGPS 1420/408 MHz footprint; optionally list CADC products |
| `list_catalogs` | Available catalogs and provenance of the bundled tables |

**Images and plots** (each returns a PNG plus JSON metadata, including the saved path)

| Tool | What it does |
|---|---|
| `list_surveys` | CGPS 1420/408 MHz, CGPS+VGPS, NVSS, SUMSS, DSS2, Pan-STARRS, IPHAS/VTSS/SHASSA Hα, AllWISE, ROSAT, Fermi |
| `render_cutout` | One survey around an object, with pulsar, host-SNR outline, PWN extent and neighbours |
| `render_multiwavelength` | Panel grid of the same field in several surveys |
| `plot_galactic_map` | Plane strip or all-sky map with the CGPS footprint, optionally over all Green SNRs |
| `plot_ppdot` | P–Ṗ diagram with PWN hosts highlighted and constant B, τ_c and Ė lines |
| `plot_population` | Scatter of PWN properties (Ė, τ_c, distance, sizes in arcmin or pc, …) |

**Colour (CIE 1931 2° vs CIE 1964 10°)**

| Tool | What it does |
|---|---|
| `list_spectrum_templates` | H II region, planetary nebula, SNR shock, Crab filaments/synchrotron/integrated, single lines, equal-energy white |
| `nebula_color` | Colour of a template or a custom spectrum (emission lines, synchrotron, blackbody, reddening) under each observer, with differences |
| `plot_chromaticity_comparison` | xy and u′v′ diagrams with both spectral loci and the templates under each observer |
| `plot_cmf_comparison` | The x̄ȳz̄ functions of both observers with the main nebular lines marked |
| `render_color_swatches` | sRGB swatches per observer next to each spectrum |
| `plot_nebula_spectrum` | A template spectrum with each observer's ȳ(λ) |

**Resources**: `pwn://catalog/pwne`, `pwn://catalog/nebulae`, `pwn://lines`, `pwn://surveys`,
`pwn://references`. **Prompts**: `summarize_pwn`, `compare_nebula_colors`.

## Notes on the science

**Bundled catalog.** Only names, associations and PWN class (filled-centre, composite, relic,
bow-shock) in `src/pwn_mcp/data/*_curated.csv` are entered by hand. Every number in `pwne.csv` and
`nebulae.csv` is produced by `scripts/build_local_catalog.py` from SIMBAD, Green's catalogue
(VizieR VII/297, 2024 October version), the ATNF catalogue and the HGPS. Pulsar distances are the
ATNF `DIST` values. PWN sizes are only filled for filled-centre remnants, where Green's diameter is
the PWN size. Rebuild with:

```bash
uv run python scripts/build_local_catalog.py
```

**CGPS.** The footprint used for `in_cgps` is approximate: 52° ≤ l ≤ 192°, −3.5° ≤ b ≤ +5.5°,
plus the high-latitude extension. Use `cgps_coverage(query_archive=true)` for the actual mosaics.
`cgps_1420` and `cgps_408` cut out the DRAO mosaics at CADC (brightness temperature, K).
`cgps_vgps_1420` uses the IRAP/CADE HiPS.

**Colorimetry.** Spectra are integrated on a 0.1 nm grid against the CIE tables from
[colour-science](https://www.colour-science.org). Template line strengths are representative
values relative to Hβ = 100, not measurements of a specific position; references are listed per
template. sRGB is defined for the 2° observer. For the 10° observer, XYZ₁₀ is treated as relative
to the 10° D65 white and adapted (CAT02) to sRGB white. That makes swatches comparable, but no
standard 10° sRGB exists. Line-dominated spectra are usually outside the sRGB gamut and are
desaturated toward white for display (`in_srgb_gamut: false`). The scotopic/photopic ratio uses
CIE 1951 V′(λ) and CIE 1924 V(λ). It explains why Hα-bright nebulae look grey by eye at the
telescope while [O III]-bright ones look greenish.

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest              # offline unit and MCP integration tests
uv run pytest -m network   # tests that contact SIMBAD, VizieR, ATNF, CADC and hips2fits
```

**Releases.** The version comes from git tags (hatch-vcs). Pushing a tag `vX.Y.Z`, or creating a
release in the GitHub UI, runs `.github/workflows/release.yml`. It builds the sdist and wheel,
attaches them to the GitHub release, publishes to PyPI via trusted publishing (when the repository
variable `PUBLISH_TO_PYPI` is `true`), and pushes `ghcr.io/wdconinc/pwn-mcp-server:{X.Y.Z, X.Y, latest}`.

## License

MIT
