"""Map and population tools."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from ..catalog import local
from . import figure_result, lazy_module, tool

live = lazy_module("pwn_mcp.catalog.live")
maps = lazy_module("pwn_mcp.imaging.maps")

Field_ = Literal[
    "edot_erg_s",
    "char_age_yr",
    "dist_kpc",
    "p0_s",
    "p1",
    "bsurf_g",
    "snr_maj_arcmin",
    "snr_size_pc",
    "pwn_size_arcmin",
    "pwn_size_pc",
    "radio_spectral_index",
    "radio_flux_1ghz_jy",
]


def register(mcp: MCPServer) -> None:
    @tool(mcp, structured_output=False)
    def plot_galactic_map(
        kinds: tuple[Literal["pwn", "snr", "hii", "pn"], ...] = ("pwn", "snr", "hii", "pn"),
        projection: Literal["plane", "allsky"] = "plane",
        show_cgps_footprint: bool = True,
        include_green_snrs: Annotated[
            bool, Field(description="Plot all 310 Green SNRs in the background (network, cached).")
        ] = False,
        label: Literal["none", "pwn", "highlight", "all"] = "pwn",
        highlight: tuple[str, ...] = (),
    ) -> list:
        """Map of bundled PWNe and other nebulae in Galactic coordinates with the CGPS footprint,
        optionally over the full Green SNR catalogue."""
        recs = [r for r in local.records() if r["kind"] in kinds]
        background, note = None, None
        if include_green_snrs:
            try:
                background = live.vizier_table("green_snr", limit=1000)
            except Exception as exc:
                note = f"Green SNRs not shown: {type(exc).__name__}: {exc}"
        fig = maps.plot_galactic_map(
            recs, background, projection, show_cgps_footprint, label, tuple(highlight)
        )
        return figure_result(
            fig,
            f"galactic_map_{projection}",
            {"objects": len(recs), "background": len(background or []), "note": note},
        )

    @tool(mcp, structured_output=False)
    def plot_ppdot(
        include_atnf: Annotated[
            bool, Field(description="Show all ATNF pulsars in grey (network, cached).")
        ] = True,
    ) -> list:
        """P–Ṗ diagram of pulsars with the PWN-powering pulsars highlighted by PWN class, and lines of
        constant magnetic field, characteristic age and spin-down power."""
        pwne = [r for r in local.records() if r["kind"] == "pwn"]
        atnf, note = None, None
        if include_atnf:
            try:
                atnf = live.pulsar_population()
            except Exception as exc:
                note = f"ATNF population not shown: {type(exc).__name__}: {exc}"
        fig = maps.plot_ppdot(pwne, atnf)
        return figure_result(
            fig,
            "ppdot",
            {
                "pwn_hosts": sum(1 for r in pwne if r.get("p0_s")),
                "atnf_pulsars": len(atnf or []),
                "note": note,
            },
        )

    @tool(mcp, structured_output=False)
    def plot_population(
        x: Field_ = "char_age_yr",
        y: Field_ = "edot_erg_s",
        log_x: bool | None = None,
        log_y: bool | None = None,
    ) -> list:
        """Scatter plot of two properties of the bundled PWNe, coloured by PWN class (e.g. Ė vs τ_c,
        PWN size in pc vs age). Physical sizes use the ATNF distance. Axes go logarithmic
        automatically when the data span more than two decades."""
        fig, n = maps.plot_population([r for r in local.records() if r["kind"] == "pwn"], x, y, log_x, log_y)
        return figure_result(fig, f"population_{y}_vs_{x}", {"points": n, "x": x, "y": y})
