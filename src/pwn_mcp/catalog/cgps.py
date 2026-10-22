"""Canadian Galactic Plane Survey (CGPS) footprint.

The CGPS (Taylor et al. 2003, AJ 125, 3145) was observed with the DRAO Synthesis Telescope in
phases; the released mosaics cover roughly 52° ≤ l ≤ 192°, -3.5° ≤ b ≤ +5.5°, with a
high-latitude extension to b ≈ +17.5° for 100° ≤ l ≤ 116.5°. The 408 MHz continuum extends
slightly further (≈ 49°-195°, -6.5° ≤ b ≤ +8.5°). These boxes are approximate; use the CADC
query in :mod:`pwn_mcp.catalog.live` for the actual mosaics at a position.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    name: str
    l_min: float
    l_max: float
    b_min: float
    b_max: float

    def contains(self, l: float, b: float) -> bool:
        return self.l_min <= l % 360 <= self.l_max and self.b_min <= b <= self.b_max


FOOTPRINTS: dict[str, tuple[Box, ...]] = {
    "1420 MHz / HI": (
        Box("main", 52.0, 192.0, -3.5, 5.5),
        Box("high-latitude extension", 100.0, 116.5, 5.5, 17.5),
    ),
    "408 MHz": (
        Box("main", 49.0, 195.0, -6.5, 8.5),
        Box("high-latitude extension", 97.0, 120.0, 8.5, 21.0),
    ),
}

DATA_ACCESS = {
    "archive": "Canadian Astronomy Data Centre (CADC), collection 'CGPS'",
    "url": "https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/cgps/",
    "hips_hi": "ivo://CDS/C/CGPS-HI",
    "reference": "Taylor et al. 2003, AJ 125, 3145",
}


def in_cgps(l: float, b: float, band: str = "1420 MHz / HI") -> bool:
    return any(box.contains(l, b) for box in FOOTPRINTS[band])


def coverage(l: float, b: float) -> dict:
    bands = {}
    for band, boxes in FOOTPRINTS.items():
        hit = next((box.name for box in boxes if box.contains(l, b)), None)
        bands[band] = {"covered": hit is not None, "region": hit}
    return {
        "l": round(l % 360, 4),
        "b": round(b, 4),
        "in_cgps": bands["1420 MHz / HI"]["covered"],
        "bands": bands,
        "footprint_note": "Approximate survey boundaries; query CADC for the actual mosaics.",
        **DATA_ACCESS,
    }
