"""Render survey cutouts with catalog overlays."""

from __future__ import annotations

import math
import warnings

import astropy.units as u
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.visualization import (
    AsinhStretch,
    ImageNormalize,
    LinearStretch,
    LogStretch,
    PercentileInterval,
    SqrtStretch,
)
from astropy.visualization.wcsaxes import SphericalCircle

from ..catalog import local
from ..plotting import INK_SECONDARY, SERIES
from .fetch import Cutout

# NaN blanking and log/sqrt of negative noise pixels are expected in survey cutouts.
warnings.filterwarnings("ignore", category=RuntimeWarning, module="astropy.visualization")
warnings.filterwarnings("ignore", message="invalid value encountered in do_format")

STRETCHES = {"linear": LinearStretch, "sqrt": SqrtStretch, "log": LogStretch, "asinh": AsinhStretch}
OVERLAYS = ("pulsar", "snr", "pwn", "neighbors", "beam")

PULSAR_COLOR = "#ffffff"
SNR_COLOR = SERIES[2]
PWN_COLOR = SERIES[3]
LABEL_FX = [pe.withStroke(linewidth=2.5, foreground="black")]


def _norm(data: np.ndarray, stretch: str, percentile: float) -> ImageNormalize:
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return ImageNormalize(vmin=0, vmax=1)
    return ImageNormalize(finite, interval=PercentileInterval(percentile), stretch=STRETCHES[stretch]())


def _draw(ax, cutout: Cutout, stretch: str | None, cmap: str | None, percentile: float):
    if cutout.data.ndim == 3:
        ax.imshow(cutout.data, origin="lower")
        return None
    norm = _norm(cutout.data, stretch or cutout.survey.stretch, percentile)
    return ax.imshow(cutout.data, origin="lower", cmap=cmap or cutout.survey.cmap, norm=norm)


def _circle(ax, center: SkyCoord, radius_arcmin: float, color: str, ls: str, label: str):
    ax.add_patch(
        SphericalCircle(
            (center.icrs.ra, center.icrs.dec),
            radius_arcmin * u.arcmin,
            transform=ax.get_transform("icrs"),
            edgecolor=color,
            facecolor="none",
            lw=1.5,
            ls=ls,
            label=label,
        )
    )


def add_overlays(ax, rec: dict | None, center: SkyCoord, fov_deg: float, overlays: tuple[str, ...]):
    tr = ax.get_transform("icrs")
    if rec:
        filled = (rec.get("snr_type") or "").startswith("F")  # for plerions the SNR *is* the PWN
        if "snr" in overlays and not filled and rec.get("snr_ra") is not None and rec.get("snr_maj_arcmin"):
            c = SkyCoord(rec["snr_ra"] * u.deg, rec["snr_dec"] * u.deg)
            _circle(ax, c, rec["snr_maj_arcmin"] / 2, SNR_COLOR, "--", f"SNR {rec['host_snr']} (Green ⌀)")
        if "pwn" in overlays and rec.get("pwn_size_arcmin"):
            _circle(ax, center, rec["pwn_size_arcmin"] / 2, PWN_COLOR, ":", "PWN extent")
        if "pulsar" in overlays and rec.get("psr_ra") is not None:
            ax.scatter(
                rec["psr_ra"],
                rec["psr_dec"],
                transform=tr,
                marker="*",
                s=160,
                color=PULSAR_COLOR,
                edgecolor="black",
                linewidth=0.8,
                zorder=5,
                label=f"PSR {rec['pulsar']}",
            )
    if "neighbors" in overlays:
        half = fov_deg / 2
        for other in local.records():
            if rec and other["name"] == rec.get("name"):
                continue
            oc = SkyCoord(other["ra"] * u.deg, other["dec"] * u.deg)
            if center.separation(oc).deg < half * 0.95:
                ax.scatter(
                    other["ra"], other["dec"], transform=tr, marker="+", s=60, color=PULSAR_COLOR, zorder=5
                )
                ax.text(
                    other["ra"],
                    other["dec"],
                    "  " + other["name"],
                    transform=tr,
                    color=PULSAR_COLOR,
                    fontsize=8,
                    path_effects=LABEL_FX,
                )


def _style_axes(ax, frame: str):
    lon, lat = ax.coords[0], ax.coords[1]
    if frame == "galactic":
        lon.set_axislabel("Galactic longitude l")
        lat.set_axislabel("Galactic latitude b")
    else:
        lon.set_axislabel("RA (ICRS)")
        lat.set_axislabel("Dec (ICRS)")
    for c in (lon, lat):
        c.set_major_formatter("d.dd")
        c.display_minor_ticks(True)
    ax.coords.grid(color="white", alpha=0.25, ls="solid", lw=0.5)


def _frame_field(ax, cutout: Cutout, center: SkyCoord, fov_deg: float):
    """Show exactly the requested field, whatever the extent of the fetched cutout."""
    x, y = cutout.wcs.world_to_pixel(center)
    half = fov_deg / 2 / abs(cutout.wcs.proj_plane_pixel_scales()[0].to_value(u.deg))
    ax.set_xlim(float(x) - half, float(x) + half)
    ax.set_ylim(float(y) - half, float(y) + half)


def _scalebar(ax, center: SkyCoord, fov_deg: float):
    """A round-number angular scale bar in the lower-left corner."""
    target = fov_deg * 60 / 4
    nice = min((1, 2, 5, 10, 15, 20, 30, 60, 120, 300), key=lambda v: abs(math.log(v / target)))
    (xa, xb), (ya, yb) = ax.get_xlim(), ax.get_ylim()
    x0, y0 = xa + 0.06 * (xb - xa), ya + 0.06 * (yb - ya)
    scale_deg = abs(ax.wcs.proj_plane_pixel_scales()[0].to_value(u.deg))
    length = nice / 60 / scale_deg
    ax.plot([x0, x0 + length], [y0, y0], color="white", lw=2.5, solid_capstyle="butt", zorder=6)
    text = f"{nice}′" if nice < 60 else f"{nice // 60}°"
    ax.text(
        x0 + length / 2,
        y0 + 0.02 * (yb - ya),
        text,
        color="white",
        ha="center",
        fontsize=8,
        path_effects=LABEL_FX,
    )


def render_cutout(
    cutout: Cutout,
    center: SkyCoord,
    fov_deg: float,
    title: str,
    rec: dict | None = None,
    overlays: tuple[str, ...] = ("pulsar", "snr", "pwn", "neighbors"),
    stretch: str | None = None,
    cmap: str | None = None,
    percentile: float = 99.5,
    frame: str = "galactic",
    ax=None,
    colorbar: bool = True,
):
    own = ax is None
    if own:
        fig = plt.figure(figsize=(7, 6.4))
        ax = fig.add_subplot(projection=cutout.wcs)
    if cutout.wcs.pixel_shape is None:
        ny, nx = cutout.data.shape[:2]
        cutout.wcs.pixel_shape = (nx, ny)
    im = _draw(ax, cutout, stretch, cmap, percentile)
    _frame_field(ax, cutout, center, fov_deg)
    add_overlays(ax, rec, center, fov_deg, overlays)
    _style_axes(ax, frame if "GLON" in cutout.wcs.wcs.ctype[0] else "icrs")
    _scalebar(ax, center, fov_deg)
    ax.set_title(title, fontsize=10)
    if own:
        if im is not None and colorbar:
            cb = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
            cb.set_label(cutout.unit or "intensity", color=INK_SECONDARY)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            leg = ax.legend(handles, labels, loc="upper right", fontsize=7.5, frameon=True, framealpha=0.6)
            leg.get_frame().set_facecolor("black")
            for t in leg.get_texts():
                t.set_color("white")
        ax.figure.text(
            0.01, 0.005, f"{cutout.survey.credit} · {cutout.backend}", fontsize=6.5, color=INK_SECONDARY
        )
        return ax.figure
    return im


def render_panels(
    cutouts: list[tuple[Cutout | None, str]],
    center: SkyCoord,
    fov_deg: float,
    title: str,
    rec: dict | None,
    overlays: tuple[str, ...],
):
    n = len(cutouts)
    ncol = min(n, 3)
    nrow = math.ceil(n / ncol)
    fig = plt.figure(figsize=(4.6 * ncol, 4.9 * nrow + 0.4))
    credits = []
    for i, (cutout, label) in enumerate(cutouts):
        if cutout is None:
            ax = fig.add_subplot(nrow, ncol, i + 1)
            ax.axis("off")
            ax.text(0.5, 0.5, label, ha="center", va="center", fontsize=9, color=INK_SECONDARY, wrap=True)
            continue
        if cutout.wcs.pixel_shape is None:
            ny, nx = cutout.data.shape[:2]
            cutout.wcs.pixel_shape = (nx, ny)
        ax = fig.add_subplot(nrow, ncol, i + 1, projection=cutout.wcs)
        render_cutout(cutout, center, fov_deg, label, rec, overlays, ax=ax)
        credits.append(cutout.survey.credit)
    fig.suptitle(title, fontsize=12)
    fig.text(0.01, 0.005, " · ".join(dict.fromkeys(credits)), fontsize=6.5, color=INK_SECONDARY, wrap=True)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97), h_pad=2.5)
    return fig
