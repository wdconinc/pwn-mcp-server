"""Galactic distribution maps and pulsar/PWN population plots."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from ..catalog.cgps import FOOTPRINTS
from ..plotting import INK, INK_MUTED, INK_SECONDARY, SERIES

KIND_STYLE = {
    "pwn": ("Pulsar wind nebula", SERIES[0], "o"),
    "snr": ("Supernova remnant", SERIES[1], "s"),
    "hii": ("H II region", SERIES[2], "D"),
    "pn": ("Planetary nebula", SERIES[3], "^"),
}
PWN_TYPE_STYLE = {
    "filled-center": ("filled-centre", SERIES[0], "o"),
    "composite": ("composite", SERIES[1], "s"),
    "relic": ("relic", SERIES[2], "D"),
    "bow-shock": ("bow shock", SERIES[3], "^"),
}
CGPS_FILL = SERIES[6]


def _wrap(l_deg: np.ndarray | float) -> np.ndarray:
    """Galactic longitude in (-180, 180]."""
    return (np.asarray(l_deg) + 180.0) % 360.0 - 180.0


def _split_at_anticenter(l_min: float, l_max: float) -> list[tuple[float, float]]:
    """Longitude range as segments in wrapped (-180, 180] coordinates, split at l = 180°."""
    a, b = _wrap(l_min), _wrap(l_max)
    if l_max - l_min >= 360:
        return [(-180.0, 180.0)]
    if a <= b:
        return [(float(a), float(b))]
    return [(float(a), 180.0), (-180.0, float(b))]


def plot_galactic_map(
    records: list[dict],
    background: list[dict] | None = None,
    projection: str = "plane",
    show_cgps: bool = True,
    label: str = "pwn",
    highlight: tuple[str, ...] = (),
):
    """Positions of catalogued objects in Galactic coordinates.

    ``projection='plane'`` is a strip |b| ≲ 12° with longitude increasing to the left;
    ``'allsky'`` is an Aitoff projection. ``background`` (e.g. Green's SNRs) is drawn as small
    grey points. ``label`` is 'none', 'pwn', 'highlight' or 'all'.
    """
    allsky = projection == "allsky"
    if allsky:
        fig = plt.figure(figsize=(11, 6))
        ax = fig.add_subplot(projection="aitoff")
        ax.grid(True, color="#d8d7d2", lw=0.5)

        def xy(l, b):
            return -np.radians(_wrap(l)), np.radians(b)
    else:
        fig, ax = plt.subplots(figsize=(14, 4.6))

        def xy(l, b):
            return _wrap(l), np.asarray(b)

    if show_cgps:
        first = True
        for box in FOOTPRINTS["1420 MHz / HI"]:
            for l0, l1 in _split_at_anticenter(box.l_min, box.l_max):
                lab = "CGPS 1420 MHz footprint" if first else None
                first = False
                if allsky:
                    lon = np.linspace(l0, l1, 60)
                    lat = np.linspace(box.b_min, box.b_max, 20)
                    edge_l = np.concatenate([lon, np.full(20, l1), lon[::-1], np.full(20, l0)])
                    edge_b = np.concatenate([np.full(60, box.b_min), lat, np.full(60, box.b_max), lat[::-1]])
                    ax.fill(
                        -np.radians(edge_l), np.radians(edge_b), color=CGPS_FILL, alpha=0.15, lw=0, label=lab
                    )
                else:
                    ax.add_patch(
                        Rectangle(
                            (l0, box.b_min),
                            l1 - l0,
                            box.b_max - box.b_min,
                            color=CGPS_FILL,
                            alpha=0.12,
                            lw=0,
                            label=lab,
                        )
                    )

    if background:
        bl = np.array([r["l"] for r in background if r.get("l") is not None])
        bb = np.array([r["b"] for r in background if r.get("b") is not None])
        x, y = xy(bl, bb)
        ax.scatter(x, y, s=8, color=INK_MUTED, alpha=0.5, lw=0, label=f"Green SNRs ({len(bl)})", zorder=2)

    for kind, (title, color, marker) in KIND_STYLE.items():
        sel = [r for r in records if r["kind"] == kind]
        if not sel:
            continue
        x, y = xy(np.array([r["l"] for r in sel]), np.array([r["b"] for r in sel]))
        ax.scatter(
            x,
            y,
            s=42,
            color=color,
            marker=marker,
            edgecolor="white",
            linewidth=1.0,
            zorder=4,
            label=f"{title} ({len(sel)})",
        )

    for r in records:
        hl = r["name"] in highlight
        if label == "all" or hl or (label == "pwn" and r["kind"] == "pwn"):
            x, y = xy(r["l"], r["b"])
            ax.annotate(
                r["name"],
                (float(x), float(y)),
                xytext=(4, 3),
                textcoords="offset points",
                fontsize=8 if hl else 6.5,
                color=INK if hl else INK_SECONDARY,
                fontweight="bold" if hl else None,
                zorder=5,
            )

    if allsky:
        ticks = np.arange(-150, 181, 30)
        ax.set_xticks(np.radians(ticks))
        ax.set_xticklabels([f"{(-t) % 360:.0f}°" for t in ticks], fontsize=7, color=INK_SECONDARY)
    else:
        bs = [r["b"] for r in records]
        lim = min(max(12.0, max(abs(b) for b in bs) + 1 if bs else 12.0), 20.0)
        ax.set_xlim(180, -180)
        ax.set_ylim(-lim, lim)
        ticks = np.arange(-180, 181, 30)
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{t % 360:.0f}°" for t in ticks])
        ax.set_xlabel("Galactic longitude l")
        ax.set_ylabel("Galactic latitude b (°)")
        ax.axhline(0, color=INK_MUTED, lw=0.6, zorder=1)
    ax.set_title(
        "Galactic distribution" + (" (objects with |b| beyond the axes are omitted)" if not allsky else "")
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14 if not allsky else -0.06), ncol=6, fontsize=8)
    fig.tight_layout()
    return fig


# --- Pulsar populations ------------------------------------------------------------------------

I_NS = 1e45  # g cm^2


def _edot(p, pdot):
    return 4 * math.pi**2 * I_NS * pdot / p**3


def plot_ppdot(pwn_records: list[dict], atnf: list[dict] | None = None):
    """P–Ṗ diagram: all ATNF pulsars in grey (if given), PWN hosts coloured by PWN class, with
    lines of constant surface field, characteristic age and spin-down power."""
    fig, ax = plt.subplots(figsize=(8.5, 7))
    if atnf:
        p = np.array([r["p0"] for r in atnf if (r.get("p0") or 0) > 0 and (r.get("p1") or 0) > 0])
        pd = np.array([r["p1"] for r in atnf if (r.get("p0") or 0) > 0 and (r.get("p1") or 0) > 0])
        ax.scatter(p, pd, s=5, color=INK_MUTED, alpha=0.45, lw=0, label=f"ATNF pulsars ({len(p)})", zorder=2)
    for t, (title, color, marker) in PWN_TYPE_STYLE.items():
        sel = [r for r in pwn_records if r.get("pwn_type") == t and r.get("p0_s") and (r.get("p1") or 0) > 0]
        if not sel:
            continue
        ax.scatter(
            [r["p0_s"] for r in sel],
            [r["p1"] for r in sel],
            s=60,
            color=color,
            marker=marker,
            edgecolor="white",
            linewidth=1.2,
            zorder=4,
            label=f"PWN host: {title} ({len(sel)})",
        )
        for r in sel:
            ax.annotate(
                r["name"],
                (r["p0_s"], r["p1"]),
                xytext=(5, 2),
                textcoords="offset points",
                fontsize=6.5,
                color=INK_SECONDARY,
                zorder=5,
            )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1e-3, 20)
    ax.set_ylim(1e-21, 1e-9)
    ps = np.logspace(-3, math.log10(20), 50)
    guides = (
        [(f"B = 10$^{{{e}}}$ G", (10.0**e / 3.2e19) ** 2 / ps) for e in (10, 12, 14)]
        + [(f"τ$_c$ = 10$^{{{e}}}$ yr", ps / (2 * 10.0**e * 3.156e7)) for e in (3, 5, 7)]
        + [(f"Ė = 10$^{{{e}}}$ erg/s", 10.0**e * ps**3 / (4 * math.pi**2 * I_NS)) for e in (33, 36, 39)]
    )
    for text, pd in guides:
        ax.plot(ps, pd, color=INK_MUTED, lw=0.7, ls="--", zorder=1)
        inside = (pd > 1.5e-21) & (pd < 0.7e-9)
        if inside.any():
            i = np.flatnonzero(inside)[len(np.flatnonzero(inside)) // 2]
            ax.annotate(text, (ps[i], pd[i]), fontsize=6.5, color=INK_MUTED, rotation=0, zorder=1)
    ax.set_xlabel("Spin period P (s)")
    ax.set_ylabel("Period derivative Ṗ (s/s)")
    ax.set_title("P–Ṗ diagram with PWN-powering pulsars")
    ax.legend(loc="lower right", fontsize=8)
    return fig


POPULATION_FIELDS = {
    "edot_erg_s": "Spin-down power Ė (erg/s)",
    "char_age_yr": "Characteristic age τ$_c$ (yr)",
    "dist_kpc": "Distance (kpc)",
    "p0_s": "Spin period P (s)",
    "p1": "Ṗ (s/s)",
    "bsurf_g": "Surface dipole field B (G)",
    "snr_maj_arcmin": "Host SNR diameter (arcmin)",
    "snr_size_pc": "Host SNR diameter (pc)",
    "pwn_size_arcmin": "PWN diameter (arcmin)",
    "pwn_size_pc": "PWN diameter (pc)",
    "radio_spectral_index": "Radio spectral index α",
    "radio_flux_1ghz_jy": "1 GHz flux density (Jy)",
}


def derived_value(r: dict, field: str) -> float | None:
    if field in ("snr_size_pc", "pwn_size_pc"):
        size = r.get("snr_maj_arcmin" if field == "snr_size_pc" else "pwn_size_arcmin")
        d = r.get("dist_kpc")
        return size / 60 * math.pi / 180 * d * 1000 if size and d else None
    return r.get(field)


def plot_population(
    records: list[dict], x: str, y: str, log_x: bool | None = None, log_y: bool | None = None
):
    fig, ax = plt.subplots(figsize=(8, 6))
    used = []
    for t, (title, color, marker) in PWN_TYPE_STYLE.items():
        pts = [
            (derived_value(r, x), derived_value(r, y), r["name"]) for r in records if r.get("pwn_type") == t
        ]
        pts = [p for p in pts if p[0] is not None and p[1] is not None]
        if not pts:
            continue
        used += pts
        ax.scatter(
            [p[0] for p in pts],
            [p[1] for p in pts],
            s=60,
            color=color,
            marker=marker,
            edgecolor="white",
            linewidth=1.2,
            label=f"{title} ({len(pts)})",
            zorder=4,
        )
        for px, py, name in pts:
            ax.annotate(
                name, (px, py), xytext=(5, 2), textcoords="offset points", fontsize=7, color=INK_SECONDARY
            )
    if not used:
        plt.close(fig)
        raise ValueError(f"No bundled PWNe have both {x} and {y}.")

    def auto_log(vals):
        v = np.array([abs(a) for a in vals if a])
        return bool(len(v)) and (np.all(np.array(vals) > 0)) and v.max() / v.min() > 100

    if log_x if log_x is not None else auto_log([p[0] for p in used]):
        ax.set_xscale("log")
    if log_y if log_y is not None else auto_log([p[1] for p in used]):
        ax.set_yscale("log")
    ax.set_xlabel(POPULATION_FIELDS.get(x, x))
    ax.set_ylabel(POPULATION_FIELDS.get(y, y))
    ax.set_title(f"{POPULATION_FIELDS.get(y, y)} vs {POPULATION_FIELDS.get(x, x)}")
    ax.legend(fontsize=8)
    return fig, len(used)
