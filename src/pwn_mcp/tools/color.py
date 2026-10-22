"""Colour tools: nebular spectra under the CIE 1931 2° and CIE 1964 10° observers."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from ..color import plots
from ..color.colorimetry import compare_observers
from ..color.observers import DEFAULT_OBSERVERS, OBSERVERS
from ..color.spectra import TEMPLATES, custom_spectrum, line_list, template_spectrum
from . import figure_result, tool

ObserverKey = Literal["cie1931_2", "cie1964_10", "cie2015_2", "cie2015_10"]
Observers = Annotated[
    tuple[ObserverKey, ...],
    Field(description="Standard observers to compare; default CIE 1931 2° and CIE 1964 10°."),
]
TemplateKeys = Annotated[tuple[str, ...], Field(description="Template keys from list_spectrum_templates.")]


def _template_spectra(templates: list[str], reddened: bool):
    return [template_spectrum(k, ebv=TEMPLATES[k].typical_ebv if reddened else None) for k in templates]


def register(mcp: MCPServer) -> None:
    @tool(mcp)
    def list_spectrum_templates() -> dict:
        """List synthetic nebular spectrum templates (H II region, planetary nebula, SNR shock,
        Crab Nebula filaments/synchrotron, single lines) and the known emission lines."""
        return {
            "templates": [
                {
                    "key": t.key,
                    "title": t.title,
                    "description": t.description,
                    "lines_rel_hbeta": t.lines,
                    "synchrotron_alpha": t.synchrotron_alpha,
                    "continuum_fraction": t.continuum_fraction,
                    "typical_ebv": t.typical_ebv,
                    "references": list(t.references),
                }
                for t in TEMPLATES.values()
            ],
            "lines": [
                {"key": ln.key, "label": ln.label, "wavelength_nm": ln.wavelength_nm}
                for ln in line_list().values()
            ],
            "observers": {k: o.label for k, o in OBSERVERS.items()},
            "note": "Template line strengths are representative, not measurements of one position.",
        }

    @tool(mcp)
    def nebula_color(
        template: Annotated[
            str | None, Field(description="Template key; omit to build a custom spectrum.")
        ] = None,
        lines: Annotated[
            dict[str, float] | None,
            Field(description="Custom emission lines: {line key, label or wavelength in nm: relative flux}."),
        ] = None,
        fwhm_kms: Annotated[float, Field(gt=0, description="Velocity FWHM for custom lines.")] = 30.0,
        synchrotron_alpha: Annotated[
            float | None,
            Field(description="Radio-to-optical spectral index α (S_ν ∝ ν^-α) for a synchrotron continuum."),
        ] = None,
        continuum_fraction: Annotated[
            float | None, Field(ge=0, le=1, description="Fraction of visible energy in the continuum.")
        ] = None,
        blackbody_k: Annotated[
            float | None, Field(gt=0, description="Use a blackbody continuum (K).")
        ] = None,
        ebv: Annotated[
            float | None,
            Field(ge=0, description="Foreground reddening E(B-V), CCM89 R_V=3.1. Omit for none."),
        ] = None,
        apply_typical_reddening: Annotated[
            bool, Field(description="Use the template's typical E(B-V) when ebv is omitted.")
        ] = False,
        observers: Observers = DEFAULT_OBSERVERS,
        include_scotopic: bool = True,
    ) -> dict:
        """Perceived colour of a nebular spectrum under each observer: XYZ, xy, u'v', CIELAB,
        sRGB hex, dominant wavelength and purity, plus Δu'v' and ΔE2000 between observers and the
        scotopic/photopic ratio (rod sensitivity, relevant to visual observing)."""
        if template:
            if template not in TEMPLATES:
                raise ValueError(f"Unknown template {template!r}; choose from {sorted(TEMPLATES)}")
            e = (
                ebv
                if ebv is not None
                else (TEMPLATES[template].typical_ebv if apply_typical_reddening else None)
            )
            spec = template_spectrum(
                template, ebv=e, alpha=synchrotron_alpha, continuum_fraction=continuum_fraction
            )
        else:
            if not lines and synchrotron_alpha is None and blackbody_k is None:
                raise ValueError(
                    "Give a template, or lines and/or a continuum (synchrotron_alpha, blackbody_k)."
                )
            spec = custom_spectrum(
                lines, fwhm_kms, synchrotron_alpha, continuum_fraction or 0.0, blackbody_k, ebv or 0.0
            )
        return compare_observers(spec, observers, include_scotopic)

    @tool(mcp, structured_output=False)
    def plot_chromaticity_comparison(
        templates: TemplateKeys = (
            "hii_region",
            "planetary_nebula",
            "snr_radiative_shock",
            "crab_composite",
            "h_alpha_only",
            "oiii_only",
        ),
        observers: Observers = DEFAULT_OBSERVERS,
        reddened: Annotated[bool, Field(description="Apply each template's typical E(B-V).")] = False,
    ) -> list:
        """CIE 1931 xy and CIE 1976 u'v' diagrams showing each observer's spectral locus and where
        each nebula template falls under each observer."""
        fig, results = plots.plot_chromaticity_comparison(_template_spectra(templates, reddened), observers)
        return figure_result(
            fig,
            "chromaticity_comparison",
            {
                "points": [
                    {"template": k, **{r.observer: {"xy": r.xy, "uv_prime": r.uv_prime} for r in rs}}
                    for k, rs in zip(templates, results, strict=True)
                ],
            },
        )

    @tool(mcp, structured_output=False)
    def plot_cmf_comparison(observers: Observers = DEFAULT_OBSERVERS) -> list:
        """Overlay the x̄ȳz̄ colour-matching functions of the chosen observers, with the main
        nebular emission lines marked."""
        return figure_result(
            plots.plot_cmf_comparison(observers), "cmf_comparison", {"observers": list(observers)}
        )

    @tool(mcp, structured_output=False)
    def render_color_swatches(
        templates: TemplateKeys = (
            "hii_region",
            "planetary_nebula",
            "snr_radiative_shock",
            "crab_composite",
            "crab_synchrotron",
        ),
        observers: Observers = DEFAULT_OBSERVERS,
        reddened: Annotated[bool, Field(description="Apply each template's typical E(B-V).")] = False,
    ) -> list:
        """Side-by-side sRGB swatches of each template's colour under each observer, next to its
        spectrum."""
        fig, rows = plots.plot_swatches(_template_spectra(templates, reddened), observers)
        return figure_result(
            fig,
            "color_swatches",
            {
                "swatches": [
                    {"template": k, **{c.observer: c.srgb_hex for c in cs}}
                    for k, cs in zip(templates, rows, strict=True)
                ],
            },
        )

    @tool(mcp, structured_output=False)
    def plot_nebula_spectrum(
        template: str,
        observers: Observers = DEFAULT_OBSERVERS,
        ebv: Annotated[float | None, Field(ge=0)] = None,
    ) -> list:
        """Plot a template spectrum with each observer's luminance function ȳ(λ) overlaid."""
        spec = template_spectrum(template, ebv=ebv)
        return figure_result(
            plots.plot_spectrum(spec, observers), f"spectrum_{template}", {"template": template, "ebv": ebv}
        )
