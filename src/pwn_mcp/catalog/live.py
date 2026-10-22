"""Live queries to SIMBAD, VizieR, the ATNF pulsar catalogue and CADC, with a disk cache.

Every function raises :class:`OfflineError` when PWN_MCP_OFFLINE is set, and caches JSON-able
results under the cache directory for ``CACHE_TTL_S`` seconds.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import warnings
from collections.abc import Callable
from typing import Any

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord

from .. import config
from .sources import VIZIER_SOURCES, VizierSource

CACHE_TTL_S = 30 * 86400

warnings.filterwarnings("ignore", module="astroquery")
warnings.filterwarnings("ignore", category=u.UnitsWarning)


class OfflineError(RuntimeError):
    pass


def require_online() -> None:
    if config.OFFLINE:
        raise OfflineError("Remote queries are disabled (PWN_MCP_OFFLINE is set).")


def cached(key: str, fn: Callable[[], Any], ttl: float = CACHE_TTL_S) -> Any:
    path = config.cache_dir("live") / (hashlib.sha256(key.encode()).hexdigest()[:24] + ".json")
    if path.exists() and time.time() - path.stat().st_mtime < ttl:
        return json.loads(path.read_text())
    require_online()
    value = fn()
    path.write_text(json.dumps(value, default=_json_default))
    return value


def _json_default(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def _clean(v):
    """Astropy/numpy cell → plain JSON value (masked/NaN → None)."""
    if v is None or np.ma.is_masked(v):
        return None
    if isinstance(v, bytes):
        v = v.decode()
    if isinstance(v, np.float32):
        v = float(f"{v:.7g}")  # drop float32 representation noise
    elif isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def _galactic(ra: float, dec: float) -> tuple[float, float]:
    g = SkyCoord(ra * u.deg, dec * u.deg).galactic
    return float(g.l.deg), float(g.b.deg)


# --- SIMBAD ------------------------------------------------------------------------------------

OTYPE_KIND = {
    "SNR": "snr",
    "PN": "pn",
    "HII": "hii",
    "PulsarWindNebula": "pwn",
    "PWN": "pwn",
    "Psr": "pulsar",
}


def simbad_lookup(name: str) -> dict | None:
    def run():
        from astroquery.simbad import Simbad

        s = Simbad()
        s.add_votable_fields("otype", "ids")
        t = s.query_object(name)
        if t is None or len(t) == 0:
            return None
        row = t[0]
        ra, dec = float(row["ra"]), float(row["dec"])
        l, b = _galactic(ra, dec)
        otype = _clean(row["otype"]) or ""
        ids = [i.strip() for i in str(row["ids"]).split("|") if i.strip()]
        return {
            "name": name,
            "main_id": _clean(row["main_id"]),
            "otype": otype,
            "kind": OTYPE_KIND.get(otype, otype.lower()),
            "ra": ra,
            "dec": dec,
            "l": l,
            "b": b,
            "aliases": ids[:40],
            "in_cgps": None,
            "source": "SIMBAD",
        }

    return cached(f"simbad:{name.strip().lower()}", run)


# --- VizieR ------------------------------------------------------------------------------------


def _rows_to_dicts(table, src: VizierSource, center: SkyCoord | None = None) -> list[dict]:
    out = []
    for row in table:
        rec = {"catalog": src.key}
        for col, field in src.columns.items():
            if col in table.colnames:
                rec[field] = _clean(row[col])
        coord = src.coord(row)
        if coord is not None:
            rec["ra"], rec["dec"] = float(coord.icrs.ra.deg), float(coord.icrs.dec.deg)
            g = coord.galactic
            rec["l"], rec["b"] = float(g.l.deg), float(g.b.deg)
            if center is not None:
                rec["sep_arcmin"] = round(float(center.separation(coord).arcmin), 3)
        out.append(rec)
    if center is not None:
        out.sort(key=lambda r: r.get("sep_arcmin", 1e9))
    return out


def vizier_cone(coord: SkyCoord, radius_arcmin: float, catalog: str, limit: int = 100) -> list[dict]:
    src = VIZIER_SOURCES[catalog]

    def run():
        from astroquery.vizier import Vizier

        v = Vizier(columns=["**"], row_limit=limit, timeout=config.TIMEOUT_S)
        res = v.query_region(coord, radius=radius_arcmin * u.arcmin, catalog=src.table)
        return _rows_to_dicts(res[0], src, coord) if len(res) else []

    key = f"vizier-cone:{src.table}:{coord.icrs.ra.deg:.5f}:{coord.icrs.dec.deg:.5f}:{radius_arcmin}:{limit}"
    return cached(key, run)


def vizier_table(catalog: str, constraints: dict[str, str] | None = None, limit: int = 1000) -> list[dict]:
    """Whole-table (or constrained) query, e.g. ``{"type": "F"}`` on Green's catalogue."""
    src = VIZIER_SOURCES[catalog]

    def run():
        from astroquery.vizier import Vizier

        v = Vizier(
            columns=["**"], row_limit=limit, timeout=config.TIMEOUT_S, column_filters=constraints or {}
        )
        res = v.get_catalogs(src.table) if not constraints else v.query_constraints(catalog=src.table)
        return _rows_to_dicts(res[0], src) if len(res) else []

    return cached(f"vizier-table:{src.table}:{json.dumps(constraints, sort_keys=True)}:{limit}", run)


# --- ATNF --------------------------------------------------------------------------------------

ATNF_PARAMS = [
    "JNAME",
    "BNAME",
    "RAJD",
    "DECJD",
    "GL",
    "GB",
    "P0",
    "P1",
    "F0",
    "EDOT",
    "AGE",
    "BSURF",
    "B_LC",
    "DM",
    "DIST",
    "DIST_DM",
    "TYPE",
    "ASSOC",
    "SURVEY",
]


def _atnf_rows(table) -> list[dict]:
    out = []
    for row in table:
        rec = {p.lower(): _clean(row[p]) for p in ATNF_PARAMS if p in table.colnames}
        out.append(rec)
    return out


def pulsar(name: str) -> dict | None:
    """ATNF parameters for one pulsar (J or B name)."""

    def run():
        import psrqpy

        q = psrqpy.QueryATNF(params=ATNF_PARAMS, psrs=[name.removeprefix("PSR ").strip()])
        rows = _atnf_rows(q.table)
        if not rows:
            return None
        rows[0]["atnf_version"] = str(q.get_version)
        return rows[0]

    return cached(f"atnf:{name.strip().upper()}", run)


def pulsars_near(coord: SkyCoord, radius_arcmin: float) -> list[dict]:
    def run():
        import psrqpy

        q = psrqpy.QueryATNF(
            params=ATNF_PARAMS,
            coord1=coord.icrs.ra.to_string(u.hourangle, sep=":"),
            coord2=coord.icrs.dec.to_string(u.deg, sep=":", alwayssign=True),
            radius=radius_arcmin / 60.0,
        )
        rows = _atnf_rows(q.table)
        for r in rows:
            if r.get("rajd") is not None:
                c = SkyCoord(r["rajd"] * u.deg, r["decjd"] * u.deg)
                r["sep_arcmin"] = round(float(coord.separation(c).arcmin), 3)
        return sorted(rows, key=lambda r: r.get("sep_arcmin", 1e9))

    key = f"atnf-cone:{coord.icrs.ra.deg:.5f}:{coord.icrs.dec.deg:.5f}:{radius_arcmin}"
    return cached(key, run)


def pulsar_population(condition: str | None = None) -> list[dict]:
    """All ATNF pulsars (optionally filtered with an ATNF condition string, e.g. 'EDOT > 1e36')."""

    def run():
        import psrqpy

        q = psrqpy.QueryATNF(
            params=["JNAME", "P0", "P1", "EDOT", "AGE", "BSURF", "GL", "GB", "DIST", "ASSOC", "TYPE"],
            condition=condition,
        )
        cols = q.table.colnames
        return [
            {c.lower(): _clean(row[c]) for c in cols if not c.endswith(("_ERR", "_REF"))} for row in q.table
        ]

    return cached(f"atnf-pop:{condition}", run)


# --- CADC (CGPS) -------------------------------------------------------------------------------


def cgps_products(coord: SkyCoord, radius_deg: float = 0.05) -> list[dict]:
    """CGPS observations/products at CADC overlapping a position."""

    def run():
        from astroquery.cadc import Cadc

        t = Cadc().query_region(coord, radius=radius_deg * u.deg, collection="CGPS")
        out = []
        for row in t:
            out.append(
                {
                    "observation_id": _clean(row["observationID"]),
                    "product_id": _clean(row["productID"]),
                    "band": _clean(row["energy_bandpassName"]),
                    "em_band": _clean(row["energy_emBand"]),
                    "data_product_type": _clean(row["dataProductType"]),
                    "publisher_id": _clean(row["publisherID"]),
                }
            )
        return out

    key = f"cadc-cgps:{coord.icrs.ra.deg:.4f}:{coord.icrs.dec.deg:.4f}:{radius_deg}"
    return cached(key, run)
