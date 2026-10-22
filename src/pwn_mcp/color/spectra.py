"""Synthetic nebular spectra: emission lines, synchrotron continua, extinction.

Line strengths in the templates are *representative* values relative to Hβ = 100,
chosen to illustrate each nebula class; they are not measurements of a particular
position in a particular object. Balmer ratios follow Case B recombination at
T_e ≈ 10^4 K (Osterbrock & Ferland 2006).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files

import numpy as np

from .observers import wavelength_grid

C_KMS = 299_792.458


@dataclass(frozen=True)
class Line:
    key: str
    label: str
    wavelength_nm: float  # air wavelength


@cache
def line_list() -> dict[str, Line]:
    """Emission lines from the bundled ``lines.csv``."""
    text = files("pwn_mcp.data").joinpath("lines.csv").read_text()
    rows = csv.DictReader(line for line in text.splitlines() if not line.startswith("#"))
    return {r["key"]: Line(r["key"], r["label"], float(r["wavelength_nm"])) for r in rows}


def resolve_line(name_or_wavelength: str | float) -> float:
    """Accept a line key (e.g. ``"OIII_5007"``), a label (``"[O III] 5007"``) or a wavelength in nm."""
    if isinstance(name_or_wavelength, (int, float)):
        return float(name_or_wavelength)
    s = str(name_or_wavelength).strip()
    lines = line_list()
    if s in lines:
        return lines[s].wavelength_nm
    for line in lines.values():
        if s.lower().replace(" ", "") == line.label.lower().replace(" ", ""):
            return line.wavelength_nm
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Unknown line {s!r}; known keys: {sorted(lines)}") from None


@dataclass
class Spectrum:
    """A spectral power distribution in relative energy units per nm on the integration grid."""

    name: str
    flux: np.ndarray
    description: str = ""
    components: dict[str, float] = field(default_factory=dict)

    @property
    def wavelength(self) -> np.ndarray:
        return wavelength_grid()

    def __add__(self, other: Spectrum) -> Spectrum:
        return Spectrum(f"{self.name} + {other.name}", self.flux + other.flux)

    def scaled(self, factor: float) -> Spectrum:
        return Spectrum(self.name, self.flux * factor, self.description, dict(self.components))

    def normalized(self) -> Spectrum:
        """Scale to unit integrated energy over 360-830 nm."""
        total = np.trapezoid(self.flux, self.wavelength)
        return self.scaled(1.0 / total) if total > 0 else self


def emission_lines(lines: dict[str | float, float], fwhm_kms: float = 30.0, name: str = "lines") -> Spectrum:
    """Gaussian emission lines with integrated fluxes ``lines`` and a common velocity FWHM.

    The minimum width is clamped to a few grid steps so narrow lines integrate correctly.
    """
    wl = wavelength_grid()
    step = wl[1] - wl[0]
    flux = np.zeros_like(wl)
    for ident, strength in lines.items():
        center = resolve_line(ident)
        sigma = max(center * fwhm_kms / C_KMS, 3 * step) / (2 * np.sqrt(2 * np.log(2)))
        flux += strength * np.exp(-0.5 * ((wl - center) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))
    return Spectrum(name, flux, components={str(k): v for k, v in lines.items()})


def synchrotron(alpha: float = 0.6, name: str | None = None) -> Spectrum:
    """Power-law continuum S_ν ∝ ν^-α, i.e. F_λ ∝ λ^(α-2), unit-normalized."""
    wl = wavelength_grid()
    spec = Spectrum(name or f"synchrotron α={alpha:g}", (wl / 550.0) ** (alpha - 2.0))
    spec.description = f"Optically thin synchrotron power law, S_ν ∝ ν^-{alpha:g}"
    return spec.normalized()


def blackbody(temperature_k: float) -> Spectrum:
    """Planck spectrum B_λ(T) (e.g. a central star), unit-normalized."""
    wl_m = wavelength_grid() * 1e-9
    h, c, k = 6.62607015e-34, 2.99792458e8, 1.380649e-23
    with np.errstate(over="ignore"):
        flux = 1.0 / (wl_m**5 * np.expm1(h * c / (wl_m * k * temperature_k)))
    return Spectrum(f"blackbody {temperature_k:g} K", flux).normalized()


def equal_energy() -> Spectrum:
    """CIE illuminant E: flat in energy per unit wavelength."""
    return Spectrum("equal energy (E)", np.ones_like(wavelength_grid()))


def ccm89_a_lambda(wavelength_nm: np.ndarray, r_v: float = 3.1) -> np.ndarray:
    """A_λ / A_V from Cardelli, Clayton & Mathis (1989), valid 0.3 ≤ x ≤ 3.3 μm⁻¹."""
    x = 1000.0 / np.asarray(wavelength_nm, dtype=float)
    a = np.empty_like(x)
    b = np.empty_like(x)
    ir = x < 1.1
    a[ir] = 0.574 * x[ir] ** 1.61
    b[ir] = -0.527 * x[ir] ** 1.61
    y = x[~ir] - 1.82
    a[~ir] = np.polyval([0.32999, -0.77530, 0.01979, 0.72085, -0.02427, -0.50447, 0.17699, 1.0], y)
    b[~ir] = np.polyval([-2.09002, 5.30260, -0.62251, -5.38434, 1.07233, 2.28305, 1.41338, 0.0], y)
    return a + b / r_v


def redden(spectrum: Spectrum, ebv: float, r_v: float = 3.1) -> Spectrum:
    """Apply foreground interstellar extinction E(B-V) with the CCM89 law."""
    if ebv == 0:
        return spectrum
    a_lambda = ccm89_a_lambda(spectrum.wavelength, r_v) * r_v * ebv
    out = Spectrum(spectrum.name, spectrum.flux * 10 ** (-0.4 * a_lambda), spectrum.description,
                   dict(spectrum.components))
    out.name = f"{spectrum.name} [E(B-V)={ebv:g}]"
    return out


# --- Templates --------------------------------------------------------------------------------

CASE_B = {"H_alpha": 286.0, "H_beta": 100.0, "H_gamma": 46.8, "H_delta": 25.9}


@dataclass(frozen=True)
class Template:
    key: str
    title: str
    description: str
    lines: dict[str, float]
    fwhm_kms: float = 30.0
    synchrotron_alpha: float | None = None
    continuum_fraction: float = 0.0  # fraction of 360-830 nm energy in the continuum
    typical_ebv: float = 0.0
    references: tuple[str, ...] = ()


TEMPLATES: dict[str, Template] = {
    t.key: t
    for t in (
        Template(
            "hii_region",
            "H II region (Orion-like)",
            "Photoionized gas around hot O/B stars: Balmer lines plus moderate [O III] and [N II].",
            {**CASE_B, "OIII_5007": 350.0, "OIII_4959": 117.0, "NII_6584": 30.0, "NII_6548": 10.0,
             "SII_6716": 5.0, "SII_6731": 6.0, "HeI_5876": 13.0, "OIII_4363": 1.5},
            typical_ebv=0.0,
            references=("Osterbrock & Ferland 2006, AGN2, Ch. 4 (Case B)",
                        "Esteban et al. 2004, MNRAS 355, 229 (Orion line ratios)"),
        ),
        Template(
            "planetary_nebula",
            "Planetary nebula (high excitation)",
            "Strong [O III] 4959/5007 relative to Hβ, He II 4686 present; classic teal-green PN.",
            {**CASE_B, "OIII_5007": 1200.0, "OIII_4959": 400.0, "NII_6584": 60.0, "NII_6548": 20.0,
             "HeII_4686": 30.0, "HeI_5876": 12.0, "NeIII_3869": 100.0, "SII_6716": 3.0,
             "SII_6731": 4.0, "ArIII_7136": 12.0},
            fwhm_kms=40.0,
            references=("Kwitter & Henry 2022, PASP 134, 022001 (PN abundances review)",),
        ),
        Template(
            "snr_radiative_shock",
            "SNR radiative shock (Cygnus Loop-like)",
            "Shock-excited filaments: [S II]/Hα ≳ 0.4, strong [N II] and [O I].",
            {**CASE_B, "NII_6584": 150.0, "NII_6548": 50.0, "SII_6716": 100.0, "SII_6731": 80.0,
             "OI_6300": 60.0, "OI_6364": 20.0, "OIII_5007": 100.0, "OIII_4959": 33.0},
            fwhm_kms=100.0,
            references=("Fesen, Blair & Kirshner 1985, ApJ 292, 29 (SNR [S II]/Hα criterion)",),
        ),
        Template(
            "crab_filaments",
            "Crab Nebula filaments",
            "Photoionized by the PWN synchrotron field: strong [O III], [N II], [S II], He I.",
            {**CASE_B, "OIII_5007": 450.0, "OIII_4959": 150.0, "NII_6584": 200.0, "NII_6548": 67.0,
             "SII_6716": 80.0, "SII_6731": 70.0, "OI_6300": 40.0, "HeI_5876": 40.0},
            fwhm_kms=1500.0,
            typical_ebv=0.52,
            references=("Davidson & Fesen 1985, ARA&A 23, 119",
                        "Hester 2008, ARA&A 46, 127"),
        ),
        Template(
            "crab_synchrotron",
            "Crab Nebula synchrotron continuum",
            "Optically thin synchrotron emission from the pulsar wind nebula itself.",
            {},
            synchrotron_alpha=0.6,
            continuum_fraction=1.0,
            typical_ebv=0.52,
            references=("Véron-Cetty & Woltjer 1993, A&A 270, 370 (optical spectral index)",),
        ),
        Template(
            "crab_composite",
            "Crab Nebula (integrated)",
            "Synchrotron continuum plus filament line emission, roughly as seen in integrated light.",
            {**CASE_B, "OIII_5007": 450.0, "OIII_4959": 150.0, "NII_6584": 200.0, "NII_6548": 67.0,
             "SII_6716": 80.0, "SII_6731": 70.0, "OI_6300": 40.0, "HeI_5876": 40.0},
            fwhm_kms=1500.0,
            synchrotron_alpha=0.6,
            continuum_fraction=0.8,
            typical_ebv=0.52,
            references=("Davidson & Fesen 1985, ARA&A 23, 119",
                        "Véron-Cetty & Woltjer 1993, A&A 270, 370"),
        ),
        Template("h_alpha_only", "Hα only", "Single Balmer line at 656.3 nm.", {"H_alpha": 100.0}),
        Template("oiii_only", "[O III] 5007 only", "Single forbidden line at 500.7 nm.",
                 {"OIII_5007": 100.0}),
        Template("equal_energy", "Equal-energy white (E)", "Flat SPD; reference white point.", {},
                 continuum_fraction=1.0),
    )
}


def template_spectrum(key: str, ebv: float | None = None, alpha: float | None = None,
                      continuum_fraction: float | None = None) -> Spectrum:
    """Build the spectrum for a template, optionally overriding reddening/continuum parameters.

    ``ebv=None`` means "unreddened" (the template's ``typical_ebv`` is only reported, not applied).
    """
    try:
        t = TEMPLATES[key]
    except KeyError:
        raise ValueError(f"Unknown template {key!r}; choose from {sorted(TEMPLATES)}") from None
    frac = t.continuum_fraction if continuum_fraction is None else continuum_fraction
    alpha = t.synchrotron_alpha if alpha is None else alpha

    parts: list[Spectrum] = []
    if t.lines and frac < 1.0:
        parts.append(emission_lines(t.lines, t.fwhm_kms).normalized().scaled(1.0 - frac))
    if frac > 0.0:
        cont = equal_energy() if key == "equal_energy" else synchrotron(alpha if alpha is not None else 0.6)
        parts.append(cont.normalized().scaled(frac))
    flux = sum(p.flux for p in parts)
    spec = Spectrum(t.title, flux, t.description, dict(t.lines))
    return redden(spec, ebv) if ebv else spec


def custom_spectrum(lines: dict[str, float] | None = None, fwhm_kms: float = 30.0,
                    synchrotron_alpha: float | None = None, continuum_fraction: float = 0.0,
                    blackbody_k: float | None = None, ebv: float = 0.0,
                    name: str = "custom") -> Spectrum:
    """Assemble a spectrum from user-supplied lines and/or a continuum."""
    parts: list[Spectrum] = []
    if lines:
        parts.append(emission_lines(lines, fwhm_kms).normalized().scaled(1.0 - continuum_fraction))
    if continuum_fraction > 0 or not lines:
        if blackbody_k is not None:
            cont = blackbody(blackbody_k)
        else:
            cont = synchrotron(synchrotron_alpha if synchrotron_alpha is not None else 0.6)
        parts.append(cont.scaled(continuum_fraction if lines else 1.0))
    spec = Spectrum(name, sum(p.flux for p in parts), components=dict(lines or {}))
    return redden(spec, ebv)
