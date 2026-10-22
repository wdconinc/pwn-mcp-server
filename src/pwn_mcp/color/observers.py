"""CIE colour-matching functions and luminous efficiency functions on a common grid.

All functions are resampled onto a fine wavelength grid so that narrow emission
lines (Gaussians of a few tenths of a nm) integrate accurately.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache, lru_cache

import colour
import numpy as np

WL_MIN, WL_MAX, WL_STEP = 360.0, 830.0, 0.1
"""Integration grid (nm). The CIE tables are defined at 1 nm over 360-830 nm."""


@lru_cache(maxsize=1)
def wavelength_grid() -> np.ndarray:
    n = round((WL_MAX - WL_MIN) / WL_STEP) + 1
    return np.linspace(WL_MIN, WL_MAX, n)


@dataclass(frozen=True)
class Observer:
    key: str
    label: str
    colour_name: str
    field_deg: int
    year: int


OBSERVERS: dict[str, Observer] = {
    o.key: o
    for o in (
        Observer("cie1931_2", "CIE 1931 2°", "CIE 1931 2 Degree Standard Observer", 2, 1931),
        Observer("cie1964_10", "CIE 1964 10°", "CIE 1964 10 Degree Standard Observer", 10, 1964),
        Observer(
            "cie2015_2", "CIE 2015 2° (cone-fundamental)", "CIE 2015 2 Degree Standard Observer", 2, 2015
        ),
        Observer(
            "cie2015_10", "CIE 2015 10° (cone-fundamental)", "CIE 2015 10 Degree Standard Observer", 10, 2015
        ),
    )
}
DEFAULT_OBSERVERS = ("cie1931_2", "cie1964_10")


def get_observer(key: str) -> Observer:
    try:
        return OBSERVERS[key]
    except KeyError:
        raise ValueError(f"Unknown observer {key!r}; choose from {sorted(OBSERVERS)}") from None


def _resample(wl: np.ndarray, values: np.ndarray) -> np.ndarray:
    return np.interp(wavelength_grid(), wl, values, left=0.0, right=0.0)


@cache
def cmfs(key: str) -> np.ndarray:
    """Return an (N, 3) array of x̄, ȳ, z̄ on :func:`wavelength_grid`."""
    msds = colour.MSDS_CMFS[get_observer(key).colour_name]
    wl = np.asarray(msds.wavelengths, dtype=float)
    vals = np.asarray(msds.values, dtype=float)
    return np.column_stack([_resample(wl, vals[:, i]) for i in range(3)])


@cache
def tabulated_cmfs(key: str) -> tuple[np.ndarray, np.ndarray]:
    """The CIE table at its native 1 nm sampling (for plotting spectral loci)."""
    msds = colour.MSDS_CMFS[get_observer(key).colour_name]
    return np.asarray(msds.wavelengths, dtype=float), np.asarray(msds.values, dtype=float)


@cache
def white_point_xy(key: str) -> np.ndarray:
    """CIE D65 chromaticity for the given observer."""
    obs = get_observer(key)
    table = colour.CCS_ILLUMINANTS.get(obs.colour_name)
    if table is not None and "D65" in table:
        return np.asarray(table["D65"], dtype=float)
    # CIE 2015 observers have no tabulated D65; integrate the D65 SPD instead.
    d65 = colour.SDS_ILLUMINANTS["D65"]
    spd = _resample(np.asarray(d65.wavelengths, float), np.asarray(d65.values, float))
    xyz = np.trapezoid(spd[:, None] * cmfs(key), wavelength_grid(), axis=0)
    return xyz[:2] / xyz.sum()


@lru_cache(maxsize=1)
def photopic_v() -> np.ndarray:
    """CIE 1924 photopic luminous efficiency V(λ)."""
    sd = colour.SDS_LEFS["CIE 1924 Photopic Standard Observer"]
    return _resample(np.asarray(sd.wavelengths, float), np.asarray(sd.values, float))


@lru_cache(maxsize=1)
def scotopic_v() -> np.ndarray:
    """CIE 1951 scotopic (rod) luminous efficiency V'(λ)."""
    sd = colour.SDS_LEFS["CIE 1951 Scotopic Standard Observer"]
    return _resample(np.asarray(sd.wavelengths, float), np.asarray(sd.values, float))


K_PHOTOPIC = 683.0  # lm/W
K_SCOTOPIC = 1700.0  # lm/W (scotopic)
