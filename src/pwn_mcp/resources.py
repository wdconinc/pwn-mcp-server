"""MCP resources (bundled tables, survey list, references) and prompts."""

from __future__ import annotations

import json
from importlib.resources import files

from mcp.server.mcpserver import MCPServer

from .catalog.cgps import DATA_ACCESS, FOOTPRINTS
from .catalog.sources import VIZIER_SOURCES
from .color.spectra import TEMPLATES
from .imaging.surveys import SURVEYS

REFERENCES = {
    "Canadian Galactic Plane Survey": "Taylor et al. 2003, AJ 125, 3145",
    "VLA Galactic Plane Survey": "Stil et al. 2006, AJ 132, 1158",
    "ATNF pulsar catalogue": "Manchester et al. 2005, AJ 129, 1993",
    "psrqpy": "Pitkin 2018, JOSS 3, 538",
    "CIE 1931 2° and CIE 1964 10° observers": "CIE 015:2018, Colorimetry, 4th edition",
    "colour-science": "Mansencal et al., Colour (Zenodo), https://www.colour-science.org",
    "Extinction law": "Cardelli, Clayton & Mathis 1989, ApJ 345, 245",
    **{s.title: s.reference for s in VIZIER_SOURCES.values()},
    **{s.title: s.credit for s in SURVEYS.values()},
    **{f"template: {t.title}": "; ".join(t.references) for t in TEMPLATES.values() if t.references},
}


def _data(name: str) -> str:
    return files("pwn_mcp.data").joinpath(name).read_text()


def register(mcp: MCPServer) -> None:
    @mcp.resource(
        "pwn://catalog/pwne",
        name="pwne",
        mime_type="text/csv",
        description="Bundled pulsar wind nebula table (generated from SIMBAD, Green, ATNF, HGPS).",
    )
    def pwne_csv() -> str:
        return _data("pwne.csv")

    @mcp.resource(
        "pwn://catalog/nebulae",
        name="nebulae",
        mime_type="text/csv",
        description="Bundled showcase SNRs, H II regions and planetary nebulae.",
    )
    def nebulae_csv() -> str:
        return _data("nebulae.csv")

    @mcp.resource(
        "pwn://lines",
        name="lines",
        mime_type="text/csv",
        description="Optical emission lines used by the colour templates (air wavelengths, nm).",
    )
    def lines_csv() -> str:
        return _data("lines.csv")

    @mcp.resource(
        "pwn://surveys",
        name="surveys",
        mime_type="application/json",
        description="Image surveys, CGPS footprint and data access.",
    )
    def surveys_json() -> str:
        return json.dumps(
            {
                "surveys": [s.to_dict() for s in SURVEYS.values()],
                "cgps": {
                    "footprints": {band: [vars(b) for b in boxes] for band, boxes in FOOTPRINTS.items()},
                    **DATA_ACCESS,
                },
            },
            indent=2,
        )

    @mcp.resource(
        "pwn://references",
        name="references",
        mime_type="application/json",
        description="Citations for catalogs, surveys, colour data and spectral templates.",
    )
    def references_json() -> str:
        return json.dumps(REFERENCES, indent=2, ensure_ascii=False)

    @mcp.prompt(title="Summarize a pulsar wind nebula")
    def summarize_pwn(name: str) -> str:
        """Gather data and images for one PWN and write a short scientific summary."""
        return (
            f"Summarize the pulsar wind nebula {name}.\n"
            f"1. Call get_nebula(name={name!r}, live=true) for the catalog record, host SNR, pulsar and "
            "TeV counterpart.\n"
            "2. If it lies in the CGPS footprint, call render_cutout with survey 'cgps_1420'; otherwise "
            "use 'nvss' or 'sumss'. Then call render_multiwavelength for a radio/optical/IR/X-ray view.\n"
            "3. Report: PWN class, distance, the pulsar's P, Ṗ, Ė and τ_c, the host SNR type and size, "
            "physical sizes in pc, multi-wavelength morphology, and open questions. Cite the catalogs "
            "used (see the pwn://references resource) and note any values that are uncertain."
        )

    @mcp.prompt(title="Compare nebular colours under CIE 1931 and CIE 1964 observers")
    def compare_nebula_colors(templates: str = "hii_region, planetary_nebula, crab_composite") -> str:
        """Compare how different nebulae look under the 2° and 10° standard observers."""
        return (
            f"Compare the colours of these nebula spectrum templates: {templates}.\n"
            "1. For each, call nebula_color (default observers cie1931_2 and cie1964_10), once "
            "unreddened and once with apply_typical_reddening=true.\n"
            "2. Call plot_chromaticity_comparison and render_color_swatches for the same templates.\n"
            "3. Explain which emission lines drive the differences (the 10° observer is more sensitive "
            "near 450-520 nm, where Hβ and [O III] lie), quote Δu'v' and ΔE2000, and use the "
            "scotopic/photopic ratio to explain why faint nebulae look grey or greenish by eye."
        )
