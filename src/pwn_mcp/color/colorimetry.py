"""Colorimetry of spectra under different CIE standard observers.

sRGB is defined for the CIE 1931 2° observer. For other observers we treat XYZ as
relative to that observer's own D65 white and chromatically adapt (CAT02) to the
sRGB white, so each observer's rendering of D65 is exactly sRGB white. This makes
the swatches comparable but is an approximation: there is no standard 10° sRGB.
"""

from __future__ import annotations

import warnings
from dataclasses import asdict, dataclass

import colour
import numpy as np

from .observers import (
    DEFAULT_OBSERVERS,
    K_PHOTOPIC,
    K_SCOTOPIC,
    cmfs,
    get_observer,
    photopic_v,
    scotopic_v,
    tabulated_cmfs,
    wavelength_grid,
    white_point_xy,
)
from .spectra import Spectrum

SRGB_WHITE_XY = np.array([0.3127, 0.3290])
REFERENCE_Y = 50.0
"""Spectra are scaled to this luminance (white = 100) before Lab/ΔE, so colour is compared
at equal lightness; emission nebulae have no intrinsic reflectance scale."""


def spectrum_to_XYZ(spectrum: Spectrum, observer: str) -> np.ndarray:
    """Unscaled tristimulus values ∫ S(λ) x̄ȳz̄(λ) dλ."""
    return np.trapezoid(spectrum.flux[:, None] * cmfs(observer), wavelength_grid(), axis=0)


def xy_from_XYZ(xyz: np.ndarray) -> np.ndarray:
    return xyz[..., :2] / np.sum(xyz, axis=-1, keepdims=True)


def uv_prime_from_XYZ(xyz: np.ndarray) -> np.ndarray:
    """CIE 1976 UCS (u', v')."""
    x, y, z = xyz[..., 0], xyz[..., 1], xyz[..., 2]
    d = x + 15 * y + 3 * z
    return np.stack([4 * x / d, 9 * y / d], axis=-1)


def uv_prime_from_xy(xy: np.ndarray) -> np.ndarray:
    x, y = xy[..., 0], xy[..., 1]
    d = -2 * x + 12 * y + 3
    return np.stack([4 * x / d, 9 * y / d], axis=-1)


def XYZ_from_xy(xy: np.ndarray, Y: float = 1.0) -> np.ndarray:
    x, y = xy
    return np.array([x * Y / y, Y, (1 - x - y) * Y / y])


def srgb_from_XYZ(xyz_rel: np.ndarray, observer: str) -> tuple[np.ndarray, bool]:
    """Display sRGB (0-1, gamma encoded) at maximum brightness, and whether it was in gamut.

    Out-of-gamut colours (typical for line-dominated spectra) are desaturated toward the
    white point just enough to make all channels non-negative, then scaled so the brightest
    channel is 1. Hue is approximately preserved; saturation is not.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rgb = colour.XYZ_to_sRGB(xyz_rel, illuminant=white_point_xy(observer),
                                 chromatic_adaptation_transform="CAT02",
                                 apply_cctf_encoding=False)
    rgb = np.asarray(rgb, dtype=float)
    in_gamut = bool(rgb.min() >= -1e-9)
    if not in_gamut:
        # Mix with equal-luminance white until the most negative channel reaches zero.
        lum = float(np.dot([0.2126, 0.7152, 0.0722], rgb))
        lum = lum if lum > 0 else float(rgb.max())
        t = -rgb.min() / (lum - rgb.min())
        rgb = rgb + t * (lum - rgb)
    rgb = np.clip(rgb / rgb.max(), 0.0, 1.0)
    return np.asarray(colour.cctf_encoding(rgb, function="sRGB")), in_gamut


def hex_from_rgb(rgb: np.ndarray) -> str:
    r, g, b = (round(255 * float(c)) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def dominant_wavelength(xy: np.ndarray, observer: str) -> dict:
    """Dominant (or complementary) wavelength and excitation purity w.r.t. the D65 white."""
    wl, vals = tabulated_cmfs(observer)
    msds = colour.MultiSpectralDistributions(vals, wl)
    xy_n = white_point_xy(observer)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lam, xy_first, xy_second = colour.dominant_wavelength(xy, xy_n, msds)
    lam = float(lam)
    complementary = lam < 0
    boundary = np.asarray(xy_second if complementary else xy_first, dtype=float)
    purity = float(np.linalg.norm(xy - xy_n) / np.linalg.norm(boundary - xy_n))
    return {
        "dominant_wavelength_nm": abs(lam),
        "complementary": complementary,
        "excitation_purity": min(purity, 1.0),
    }


@dataclass
class ObserverColor:
    observer: str
    observer_label: str
    XYZ: list[float]
    xy: list[float]
    uv_prime: list[float]
    uv_1960: list[float]
    Lab: list[float]
    srgb_hex: str
    srgb: list[float]
    in_srgb_gamut: bool
    dominant_wavelength_nm: float
    complementary_wavelength: bool
    excitation_purity: float

    def to_dict(self) -> dict:
        return asdict(self)


def observer_color(spectrum: Spectrum, observer: str) -> ObserverColor:
    obs = get_observer(observer)
    xyz = spectrum_to_XYZ(spectrum, observer)
    xy = xy_from_XYZ(xyz)
    xyz_rel = xyz / xyz[1] * (REFERENCE_Y / 100.0)
    uvp = uv_prime_from_XYZ(xyz)
    white = white_point_xy(observer)
    lab = colour.XYZ_to_Lab(xyz_rel, illuminant=white)
    rgb, in_gamut = srgb_from_XYZ(xyz_rel, observer)
    dom = dominant_wavelength(xy, observer)
    return ObserverColor(
        observer=observer,
        observer_label=obs.label,
        XYZ=_r(xyz_rel * 100),
        xy=_r(xy),
        uv_prime=_r(uvp),
        uv_1960=_r([uvp[0], uvp[1] * 2 / 3]),
        Lab=_r(lab, 3),
        srgb_hex=hex_from_rgb(rgb),
        srgb=_r(rgb),
        in_srgb_gamut=in_gamut,
        dominant_wavelength_nm=round(dom["dominant_wavelength_nm"], 1),
        complementary_wavelength=dom["complementary"],
        excitation_purity=round(dom["excitation_purity"], 4),
    )


def scotopic_ratio(spectrum: Spectrum) -> dict:
    """Scotopic/photopic (S/P) luminance ratio. High S/P means relatively brighter to rods;
    faint nebulae seen by eye through a telescope are rod-dominated and appear colourless."""
    wl = wavelength_grid()
    p = K_PHOTOPIC * np.trapezoid(spectrum.flux * photopic_v(), wl)
    s = K_SCOTOPIC * np.trapezoid(spectrum.flux * scotopic_v(), wl)
    return {"photopic": float(p), "scotopic": float(s), "s_over_p": float(s / p) if p else None}


def compare_observers(spectrum: Spectrum, observers: tuple[str, ...] | list[str] = DEFAULT_OBSERVERS,
                      include_scotopic: bool = True) -> dict:
    """Colour of one spectrum under several observers, with pairwise differences."""
    results = [observer_color(spectrum, o) for o in observers]
    out: dict = {
        "spectrum": spectrum.name,
        "description": spectrum.description,
        "observers": [r.to_dict() for r in results],
        "differences": [],
        "notes": [
            (f"XYZ/Lab are scaled to Y={REFERENCE_Y:g} (white=100) so colours are compared at equal "
             "lightness; chromaticities (xy, u'v') do not depend on this."),
            ("Lab and sRGB use each observer's own D65 white; non-2° observers are mapped to sRGB "
             "via CAT02 adaptation of their D65 white to sRGB white (approximation)."),
        ],
    }
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            a, b = results[i], results[j]
            out["differences"].append({
                "pair": [a.observer, b.observer],
                "delta_xy": round(float(np.linalg.norm(np.subtract(a.xy, b.xy))), 5),
                "delta_uv_prime": round(float(np.linalg.norm(np.subtract(a.uv_prime, b.uv_prime))), 5),
                "delta_E2000": round(float(colour.delta_E(a.Lab, b.Lab, method="CIE 2000")), 3),
                "delta_dominant_wavelength_nm": round(
                    b.dominant_wavelength_nm - a.dominant_wavelength_nm, 2),
                "srgb": [a.srgb_hex, b.srgb_hex],
            })
    if include_scotopic:
        out["scotopic"] = scotopic_ratio(spectrum)
    return out


def _r(values, ndigits: int = 5) -> list[float]:
    return [round(float(v), ndigits) for v in np.asarray(values).ravel()]
