"""Shared matplotlib setup and figure export."""

from __future__ import annotations

import io
import re
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from . import config

# Categorical slots (validated reference palette) and neutral inks.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#8a8985"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

OBSERVER_COLORS = {"cie1931_2": SERIES[0], "cie1964_10": SERIES[1],
                   "cie2015_2": SERIES[2], "cie2015_10": SERIES[6]}
OBSERVER_STYLES = {"cie1931_2": "-", "cie1964_10": "--", "cie2015_2": "-.", "cie2015_10": ":"}

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": INK_MUTED,
    "axes.labelcolor": INK_SECONDARY,
    "axes.titlecolor": INK,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "lines.linewidth": 2.0,
    "legend.frameon": False,
    "font.size": 10,
    "axes.titlesize": 11,
    "figure.dpi": 110,
})


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()[:60] or "figure"


def save_figure(fig, stem: str, dpi: int = 110) -> tuple[bytes, Path]:
    """Render to PNG bytes and save a copy under the output directory."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    data = buf.getvalue()
    path = config.output_dir() / f"{slug(stem)}_{time.strftime('%Y%m%d-%H%M%S')}.png"
    path.write_bytes(data)
    return data, path
