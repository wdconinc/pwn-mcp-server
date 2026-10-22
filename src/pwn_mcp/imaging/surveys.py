"""Image surveys available for cutouts."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Survey:
    key: str
    title: str
    band: str
    backend: str  # "cadc" (CGPS mosaics) or "hips" (CDS hips2fits)
    hips_id: str | None = None
    cadc_product: str | None = None
    rgb: bool = False
    unit: str = ""
    resolution_arcsec: float | None = None
    coverage: str = "all-sky"
    cmap: str = "inferno"
    stretch: str = "asinh"
    credit: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


SURVEYS: dict[str, Survey] = {
    s.key: s
    for s in (
        Survey(
            "cgps_1420",
            "CGPS 1420 MHz continuum (Stokes I)",
            "radio 21 cm",
            "cadc",
            hips_id="ov-gso/P/CGPS/VGPS/CONT",
            cadc_product="1420MHz",
            unit="K (Tb)",
            resolution_arcsec=60,
            coverage="Galactic plane, l ≈ 52°-192°, -3.5° < b < +5.5°",
            credit="Canadian Galactic Plane Survey (Taylor et al. 2003), DRAO/NRC; data from CADC",
        ),
        Survey(
            "cgps_408",
            "CGPS 408 MHz continuum",
            "radio 74 cm",
            "cadc",
            cadc_product="408MHz",
            unit="K (Tb)",
            resolution_arcsec=210,
            coverage="Galactic plane, l ≈ 49°-195°, -6.5° < b < +8.5°",
            credit="Canadian Galactic Plane Survey (Taylor et al. 2003), DRAO/NRC; data from CADC",
        ),
        Survey(
            "cgps_vgps_1420",
            "CGPS + VGPS 1420 MHz continuum (HiPS)",
            "radio 21 cm",
            "hips",
            hips_id="ov-gso/P/CGPS/VGPS/CONT",
            unit="K",
            resolution_arcsec=60,
            coverage="Galactic plane, l ≈ 18°-192°",
            credit="CGPS (Taylor et al. 2003) + VGPS (Stil et al. 2006); HiPS by D. Paradis (IRAP/CADE)",
        ),
        Survey(
            "nvss",
            "NVSS 1.4 GHz",
            "radio 21 cm",
            "hips",
            hips_id="CDS/P/NVSS",
            unit="Jy/beam",
            resolution_arcsec=45,
            coverage="δ > -40°",
            credit="NRAO VLA Sky Survey (Condon et al. 1998)",
        ),
        Survey(
            "sumss",
            "SUMSS 843 MHz",
            "radio 36 cm",
            "hips",
            hips_id="CDS/P/SUMSS",
            unit="Jy/beam",
            resolution_arcsec=45,
            coverage="δ < -30°",
            credit="Sydney University Molonglo Sky Survey (Bock et al. 1999)",
        ),
        Survey(
            "dss2_color",
            "DSS2 colour",
            "optical",
            "hips",
            hips_id="CDS/P/DSS2/color",
            rgb=True,
            resolution_arcsec=1.7,
            credit="Digitized Sky Survey (STScI/AURA); HiPS by CDS",
        ),
        Survey(
            "panstarrs_color",
            "Pan-STARRS DR1 colour (i, r, g)",
            "optical",
            "hips",
            hips_id="CDS/P/PanSTARRS/DR1/color-i-r-g",
            rgb=True,
            resolution_arcsec=1.0,
            coverage="δ > -30°",
            credit="Pan-STARRS1 DR1 (Chambers et al. 2016); HiPS by CDS",
        ),
        Survey(
            "iphas_halpha",
            "IPHAS DR2 Hα",
            "optical Hα",
            "hips",
            hips_id="CDS/P/IPHAS/DR2/halpha",
            resolution_arcsec=1.0,
            coverage="northern Galactic plane, |b| < 5°",
            cmap="gray",
            credit="IPHAS DR2 (Barentsen et al. 2014)",
        ),
        Survey(
            "vtss_halpha",
            "VTSS Hα (continuum corrected)",
            "optical Hα",
            "hips",
            hips_id="CDS/P/VTSS/HaCC",
            resolution_arcsec=96,
            coverage="northern sky",
            cmap="gray",
            credit="Virginia Tech Spectral-line Survey (Dennison et al. 1998)",
        ),
        Survey(
            "shassa_halpha",
            "SHASSA Hα",
            "optical Hα",
            "hips",
            hips_id="CDS/P/SHASSA/H",
            resolution_arcsec=48,
            coverage="southern sky",
            cmap="gray",
            credit="Southern H-Alpha Sky Survey Atlas (Gaustad et al. 2001)",
        ),
        Survey(
            "wise_color",
            "AllWISE colour (W4, W2, W1)",
            "mid-infrared",
            "hips",
            hips_id="CDS/P/allWISE/color",
            rgb=True,
            resolution_arcsec=6,
            credit="AllWISE (Wright et al. 2010; Cutri et al. 2013); HiPS by CDS",
        ),
        Survey(
            "rass",
            "ROSAT All-Sky Survey 0.1-2.4 keV",
            "X-ray",
            "hips",
            hips_id="CDS/P/RASS",
            unit="counts",
            resolution_arcsec=45,
            cmap="magma",
            credit="ROSAT All-Sky Survey (Voges et al. 1999)",
        ),
        Survey(
            "fermi_color",
            "Fermi-LAT colour",
            "gamma-ray",
            "hips",
            hips_id="CDS/P/Fermi/color",
            rgb=True,
            resolution_arcsec=1800,
            credit="Fermi-LAT (NASA/DOE); HiPS by CDS",
        ),
    )
}


def get_survey(key: str) -> Survey:
    try:
        return SURVEYS[key]
    except KeyError:
        raise ValueError(f"Unknown survey {key!r}; choose from {sorted(SURVEYS)}") from None
