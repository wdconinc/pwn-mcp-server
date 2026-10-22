"""VizieR catalogs used for live queries, with column mappings to friendly field names."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from astropy.coordinates import SkyCoord


@dataclass(frozen=True)
class VizierSource:
    key: str
    table: str
    title: str
    kind: str
    reference: str
    columns: dict[str, str] = field(default_factory=dict)
    ra_col: str | None = None
    dec_col: str | None = None
    sexagesimal: bool = False
    glon_col: str | None = None
    glat_col: str | None = None

    def coord(self, row) -> SkyCoord | None:
        import astropy.units as u
        from astropy.coordinates import SkyCoord

        try:
            if self.glon_col and self.glat_col:
                return SkyCoord(
                    l=float(row[self.glon_col]) * u.deg, b=float(row[self.glat_col]) * u.deg, frame="galactic"
                )
            if self.ra_col and self.dec_col:
                if self.sexagesimal:
                    return SkyCoord(str(row[self.ra_col]), str(row[self.dec_col]), unit=(u.hourangle, u.deg))
                return SkyCoord(float(row[self.ra_col]) * u.deg, float(row[self.dec_col]) * u.deg)
        except (ValueError, TypeError, KeyError):
            return None
        return None


VIZIER_SOURCES: dict[str, VizierSource] = {
    s.key: s
    for s in (
        VizierSource(
            "green_snr",
            "VII/297/snrs",
            "Green's catalogue of Galactic SNRs (2024/2025, 310 SNRs)",
            "snr",
            "Green 2025, J. Astrophys. Astron. 46, 14",
            {
                "SNR": "name",
                "MajDiam": "maj_arcmin",
                "MinDiam": "min_arcmin",
                "type": "snr_type",
                "S(1GHz)": "flux_1ghz_jy",
                "Sp-Index": "spectral_index",
                "Names": "other_names",
            },
            ra_col="RAJ2000",
            dec_col="DEJ2000",
            sexagesimal=True,
        ),
        VizierSource(
            "hgps",
            "J/A+A/612/A1/sources",
            "H.E.S.S. Galactic Plane Survey sources",
            "tev",
            "H.E.S.S. Collaboration 2018, A&A 612, A1",
            {
                "Source": "name",
                "Class": "class",
                "IdObject": "identified_object",
                "Size": "size_deg",
                "SqrtTS": "sqrt_ts",
            },
            glon_col="GLON",
            glat_col="GLAT",
        ),
        VizierSource(
            "sharpless",
            "VII/20/catalog",
            "Sharpless catalogue of H II regions (Sh 2)",
            "hii",
            "Sharpless 1959, ApJS 4, 257",
            {
                "Sh2": "name",
                "Diam": "diam_arcmin",
                "Form": "form",
                "Struct": "structure",
                "Bright": "brightness",
            },
            glon_col="GLon",
            glat_col="GLat",
        ),
        VizierSource(
            "wise_hii",
            "J/ApJS/212/1/wisecat",
            "WISE catalog of Galactic H II regions",
            "hii",
            "Anderson et al. 2014, ApJS 212, 1",
            {"WISE": "name", "Cl": "class", "Rad": "radius_arcsec", "HIIName": "hii_name"},
            glon_col="GLON",
            glat_col="GLAT",
        ),
        VizierSource(
            "strasbourg_pn",
            "V/84/main",
            "Strasbourg-ESO catalogue of Galactic planetary nebulae",
            "pn",
            "Acker et al. 1992",
            {"PNG": "png", "Name": "name", "PK": "pk"},
            ra_col="_RA.icrs",
            dec_col="_DE.icrs",
            sexagesimal=True,
        ),
    )
}
