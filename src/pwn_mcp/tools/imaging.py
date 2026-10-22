"""Imaging tools: survey cutouts (CGPS, NVSS, optical, Hα, IR, X-ray, gamma) with overlays."""

from __future__ import annotations

from typing import Annotated, Literal

import numpy as np
from mcp.server.mcpserver import MCPServer
from pydantic import Field

from ..imaging import fetch, render
from ..imaging.surveys import SURVEYS, get_survey
from . import figure_result, tool
from .catalog import resolve_position

SurveyKey = Literal[
    "cgps_1420",
    "cgps_408",
    "cgps_vgps_1420",
    "nvss",
    "sumss",
    "dss2_color",
    "panstarrs_color",
    "iphas_halpha",
    "vtss_halpha",
    "shassa_halpha",
    "wise_color",
    "rass",
    "fermi_color",
]
Overlay = Literal["pulsar", "snr", "pwn", "neighbors"]
Stretch = Literal["linear", "sqrt", "log", "asinh"]


def _default_fov(rec: dict | None) -> float:
    """Field of view (deg) that frames the host SNR or PWN with some margin."""
    if rec:
        size = rec.get("snr_maj_arcmin") or rec.get("size_arcmin") or rec.get("pwn_size_arcmin")
        if size:
            return min(max(size * 2.0 / 60, 0.1), 5.0)
    return 0.5


def register(mcp: MCPServer) -> None:
    @tool(mcp)
    def list_surveys() -> dict:
        """Image surveys available to render_cutout / render_multiwavelength, with band, coverage,
        resolution and credit."""
        return {"surveys": [s.to_dict() for s in SURVEYS.values()]}

    @tool(mcp, structured_output=False)
    def render_cutout(
        name: Annotated[str | None, Field(description="Object name (bundled catalog or SIMBAD).")] = None,
        ra: float | None = None,
        dec: float | None = None,
        l: float | None = None,
        b: float | None = None,
        survey: SurveyKey = "cgps_1420",
        fov_arcmin: Annotated[
            float | None, Field(gt=0, le=600, description="Field of view; default frames the SNR/PWN.")
        ] = None,
        overlays: tuple[Overlay, ...] = ("pulsar", "snr", "pwn", "neighbors"),
        stretch: Stretch | None = None,
        cmap: Annotated[str | None, Field(description="Matplotlib colormap for single-band images.")] = None,
        percentile: Annotated[float, Field(gt=50, le=100)] = 99.5,
        frame: Literal["galactic", "icrs"] = "galactic",
    ) -> list:
        """Survey image around a nebula with the pulsar, host-SNR outline (Green diameter), PWN
        extent and neighbouring catalogued objects overlaid. CGPS images are native-resolution
        cutouts of the DRAO mosaics at CADC; other surveys come from CDS hips2fits."""
        coord, rec = resolve_position(name, ra, dec, l, b)
        fov = fov_arcmin / 60 if fov_arcmin else _default_fov(rec)
        s = get_survey(survey)
        cut = fetch.fetch(s, coord, fov, frame=frame)
        title = f"{name or 'target'} — {s.title}"
        fig = render.render_cutout(
            cut, coord, fov, title, rec, tuple(overlays), stretch, cmap, percentile, frame
        )
        stats = None
        if cut.data.ndim == 2 and np.isfinite(cut.data).any():
            stats = {
                k: float(f(cut.data))
                for k, f in (("min", np.nanmin), ("median", np.nanmedian), ("max", np.nanmax))
            }
        return figure_result(
            fig,
            f"{name or 'cutout'}_{survey}",
            {
                "survey": s.to_dict(),
                "backend": cut.backend,
                "origin": cut.origin,
                "center": {
                    "ra": coord.icrs.ra.deg,
                    "dec": coord.icrs.dec.deg,
                    "l": coord.galactic.l.deg,
                    "b": coord.galactic.b.deg,
                },
                "fov_arcmin": round(fov * 60, 3),
                "unit": cut.unit,
                "pixel_stats": stats,
            },
        )

    @tool(mcp, structured_output=False)
    def render_multiwavelength(
        name: str | None = None,
        ra: float | None = None,
        dec: float | None = None,
        l: float | None = None,
        b: float | None = None,
        surveys: tuple[SurveyKey, ...] = (
            "cgps_1420",
            "nvss",
            "dss2_color",
            "wise_color",
            "rass",
            "fermi_color",
        ),
        fov_arcmin: Annotated[float | None, Field(gt=0, le=600)] = None,
        overlays: tuple[Overlay, ...] = ("pulsar", "snr", "pwn"),
    ) -> list:
        """Panel grid of the same field in several surveys (radio, optical, IR, X-ray, gamma-ray).
        Surveys that do not cover the position are shown as empty panels with the reason."""
        coord, rec = resolve_position(name, ra, dec, l, b)
        fov = fov_arcmin / 60 if fov_arcmin else _default_fov(rec)
        panels, used = [], []
        for key in surveys:
            s = get_survey(key)
            try:
                cut = fetch.fetch(s, coord, fov)
                panels.append((cut, s.title))
                used.append({"survey": key, "backend": cut.backend, "origin": cut.origin})
            except Exception as exc:
                panels.append((None, f"{s.title}\nunavailable: {type(exc).__name__}: {exc}"[:200]))
                used.append({"survey": key, "error": f"{type(exc).__name__}: {exc}"})
        fig = render.render_panels(panels, coord, fov, name or "target", rec, tuple(overlays))
        return figure_result(
            fig, f"{name or 'field'}_multiwavelength", {"fov_arcmin": round(fov * 60, 3), "panels": used}
        )
