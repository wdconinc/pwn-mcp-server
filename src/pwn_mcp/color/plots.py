"""Figures comparing standard observers and nebular colours."""

from __future__ import annotations

import warnings

import colour
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon

from ..plotting import (
    INK,
    INK_MUTED,
    INK_SECONDARY,
    OBSERVER_COLORS,
    OBSERVER_STYLES,
    SERIES,
)
from .colorimetry import observer_color, uv_prime_from_xy, xy_from_XYZ
from .observers import DEFAULT_OBSERVERS, cmfs, get_observer, tabulated_cmfs, wavelength_grid
from .spectra import Spectrum

CMF_COLORS = (SERIES[1], SERIES[2], SERIES[0])  # x̄ orange, ȳ aqua, z̄ blue
SRGB_PRIMARIES_XY = np.array([[0.64, 0.33], [0.30, 0.60], [0.15, 0.06]])


def plot_cmf_comparison(observers=DEFAULT_OBSERVERS):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for obs in observers:
        wl, vals = tabulated_cmfs(obs)
        for i, name in enumerate(("x̄", "ȳ", "z̄")):
            ax.plot(wl, vals[:, i], color=CMF_COLORS[i], ls=OBSERVER_STYLES[obs],
                    label=f"{name} — {get_observer(obs).label}")
    ax.set_xlim(360, 830)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Tristimulus value")
    ax.set_title("CIE colour-matching functions: " + " vs ".join(get_observer(o).label for o in observers))
    ax.legend(ncol=len(observers), fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    _mark_lines(ax)
    return fig


def _mark_lines(ax):
    """Annotate the main nebular lines along the top of a wavelength axis."""
    for wl, label in ((486.1, "Hβ"), (500.7, "[O III]"), (656.3, "Hα"), (671.6, "[S II]")):
        ax.axvline(wl, color=INK_MUTED, lw=0.6, ls=":", zorder=0)
        ax.annotate(label, (wl, 1.0), xycoords=("data", "axes fraction"), xytext=(2, -10),
                    textcoords="offset points", fontsize=7, color=INK_SECONDARY)


def _locus(obs: str, space: str) -> np.ndarray:
    wl, vals = tabulated_cmfs(obs)
    keep = (wl >= 380) & (wl <= 700)
    xy = xy_from_XYZ(vals[keep])
    return uv_prime_from_xy(xy) if space == "uv" else xy


def _fill_locus(ax, locus: np.ndarray, space: str):
    """Faint sRGB rendering of the 2° chromaticity gamut, as a background reference."""
    n = 240
    xs = np.linspace(0, 0.8, n)
    ys = np.linspace(0, 0.9, n)
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    if space == "uv":
        u, v = pts[:, 0], pts[:, 1]
        d = 6 * u - 16 * v + 12
        xy = np.column_stack([9 * u / d, 4 * v / d])
    else:
        xy = pts
    xyz = np.column_stack([xy[:, 0] / np.maximum(xy[:, 1], 1e-6), np.ones(len(xy)),
                           (1 - xy[:, 0] - xy[:, 1]) / np.maximum(xy[:, 1], 1e-6)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rgb = np.asarray(colour.XYZ_to_sRGB(xyz, apply_cctf_encoding=False))
    rgb = np.clip(rgb, 0, None)
    rgb = rgb / np.maximum(rgb.max(axis=1, keepdims=True), 1e-9)
    rgb = colour.cctf_encoding(np.clip(rgb, 0, 1), function="sRGB")
    from matplotlib.path import Path

    inside = Path(np.vstack([locus, locus[:1]])).contains_points(pts)
    rgba = np.zeros((len(pts), 4))
    rgba[:, :3] = rgb
    rgba[:, 3] = np.where(inside, 0.35, 0.0)
    ax.imshow(rgba.reshape(n, n, 4), origin="lower", extent=(0, 0.8, 0, 0.9), interpolation="bilinear",
              zorder=0, aspect="auto")


def plot_chromaticity_comparison(spectra: list[Spectrum], observers=DEFAULT_OBSERVERS):
    """xy (CIE 1931) and u'v' (CIE 1976 UCS) diagrams with each observer's spectral locus and the
    chromaticities of the given spectra under each observer."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
    results = [[observer_color(s, o) for o in observers] for s in spectra]
    for ax, space in zip(axes, ("xy", "uv")):
        _fill_locus(ax, _locus("cie1931_2", space), space)
        for obs in observers:
            loc = _locus(obs, space)
            ax.plot(*np.vstack([loc, loc[:1]]).T, color=OBSERVER_COLORS[obs], ls=OBSERVER_STYLES[obs],
                    lw=1.5, label=f"{get_observer(obs).label} spectral locus")
        gamut = SRGB_PRIMARIES_XY if space == "xy" else uv_prime_from_xy(SRGB_PRIMARIES_XY)
        ax.add_patch(Polygon(gamut, closed=True, fill=False, ec=INK_MUTED, lw=0.8, ls="-"))
        ax.annotate("sRGB", gamut[0], xytext=(4, 0), textcoords="offset points", fontsize=7,
                    color=INK_MUTED)
        for spec, res in zip(spectra, results):
            pts = np.array([r.xy if space == "xy" else r.uv_prime for r in res])
            ax.plot(*pts.T, color=INK_SECONDARY, lw=0.8, zorder=3)
            for obs, p in zip(observers, pts):
                ax.scatter(*p, s=46, color=OBSERVER_COLORS[obs], edgecolor="white", linewidth=1.2,
                           zorder=4)
        for k, res in enumerate(results, start=1):
            p = np.array(res[0].xy if space == "xy" else res[0].uv_prime)
            ax.annotate(str(k), p, xytext=(-9, 5), textcoords="offset points", fontsize=8,
                        fontweight="bold", color=INK, zorder=5)
        if space == "xy":
            ax.set(xlim=(0, 0.8), ylim=(0, 0.9), xlabel="x", ylabel="y",
                   title="CIE 1931 xy chromaticity")
        else:
            ax.set(xlim=(0, 0.65), ylim=(0, 0.62), xlabel="u′", ylabel="v′",
                   title="CIE 1976 UCS u′v′ chromaticity")
        ax.set_aspect("equal")
    handles, labels = axes[0].get_legend_handles_labels()
    for obs in observers:
        handles.append(plt.Line2D([], [], marker="o", ls="", color=OBSERVER_COLORS[obs],
                                  markeredgecolor="white"))
        labels.append(f"spectrum under {get_observer(obs).label}")
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, 0.06))
    key = "   ".join(f"{k}  {s.name}" for k, s in enumerate(spectra, start=1))
    fig.text(0.5, 0.01, key, ha="center", fontsize=8, color=INK_SECONDARY, wrap=True)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    return fig, results


def _display_flux(spectrum: Spectrum, fwhm_nm: float = 1.5) -> np.ndarray:
    """Smooth for display only, so sub-nm emission lines are visible; normalized to peak 1."""
    wl = wavelength_grid()
    step = wl[1] - wl[0]
    sigma = fwhm_nm / (2 * np.sqrt(2 * np.log(2))) / step
    half = int(4 * sigma)
    kernel = np.exp(-0.5 * (np.arange(-half, half + 1) / sigma) ** 2)
    f = np.convolve(spectrum.flux, kernel / kernel.sum(), mode="same")
    return f / f.max()


def plot_swatches(spectra: list[Spectrum], observers=DEFAULT_OBSERVERS):
    """One row per spectrum: the SPD and a colour swatch per observer."""
    n = len(spectra)
    fig, axes = plt.subplots(n, 1 + len(observers), figsize=(3.2 + 1.9 * len(observers), 1.5 * n + 0.6),
                             gridspec_kw={"width_ratios": [2.6] + [1] * len(observers)}, squeeze=False)
    wl = wavelength_grid()
    ybar = cmfs("cie1931_2")[:, 1]
    rows = []
    for i, spec in enumerate(spectra):
        ax = axes[i, 0]
        f = _display_flux(spec)
        ax.fill_between(wl, f, color=INK_SECONDARY, lw=0, alpha=0.85)
        ax.plot(wl, ybar / ybar.max(), color=SERIES[2], lw=1, ls=":")
        ax.set_xlim(360, 830)
        ax.set_yticks([])
        ax.grid(False)
        ax.set_title(spec.name, loc="left", fontsize=9)
        if i < n - 1:
            ax.set_xticklabels([])
        colors = [observer_color(spec, o) for o in observers]
        rows.append(colors)
        for j, c in enumerate(colors):
            sax = axes[i, 1 + j]
            sax.set_facecolor(c.srgb_hex)
            sax.set_xticks([])
            sax.set_yticks([])
            sax.grid(False)
            for side in sax.spines.values():
                side.set_visible(False)
            sax.text(0.5, -0.12, c.srgb_hex + ("" if c.in_srgb_gamut else " *"), transform=sax.transAxes,
                     ha="center", va="top", fontsize=8, color=INK_SECONDARY)
            if i == 0:
                sax.set_title(get_observer(observers[j]).label, fontsize=9)
    axes[-1, 0].set_xlabel("Wavelength (nm)  ·  dotted: photopic ȳ(λ)  ·  lines smoothed to 1.5 nm")
    fig.text(0.99, 0.005, "* outside sRGB gamut: desaturated toward white for display", ha="right",
             fontsize=7, color=INK_MUTED)
    fig.tight_layout()
    return fig, rows


def plot_spectrum(spectrum: Spectrum, observers=DEFAULT_OBSERVERS):
    """The SPD with each observer's ȳ (luminance) function overlaid."""
    fig, ax = plt.subplots(figsize=(8, 3.6))
    wl = wavelength_grid()
    ax.fill_between(wl, _display_flux(spectrum), color=INK_SECONDARY, alpha=0.85, lw=0,
                    label="relative energy (smoothed to 1.5 nm)")
    for obs in observers:
        y = cmfs(obs)[:, 1]
        ax.plot(wl, y / y.max(), color=OBSERVER_COLORS[obs], ls=OBSERVER_STYLES[obs], lw=1.5,
                label=f"ȳ(λ) {get_observer(obs).label}")
    ax.set(xlim=(360, 830), ylim=(0, 1.05), xlabel="Wavelength (nm)", ylabel="Normalized",
           title=spectrum.name)
    ax.legend(fontsize=8, loc="upper right")
    return fig
