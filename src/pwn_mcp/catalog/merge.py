"""Combine a bundled record with live SIMBAD / VizieR / ATNF / CADC information."""

from __future__ import annotations

import astropy.units as u
from astropy.coordinates import SkyCoord

from . import live


def _attempt(out: dict, key: str, fn) -> None:
    try:
        out[key] = fn()
    except live.OfflineError as exc:
        out.setdefault("live_errors", {})[key] = str(exc)
    except Exception as exc:  # network/service failures must not break the lookup
        out.setdefault("live_errors", {})[key] = f"{type(exc).__name__}: {exc}"


def enrich(rec: dict) -> dict:
    out = dict(rec)
    coord = SkyCoord(rec["ra"] * u.deg, rec["dec"] * u.deg)
    out["live"] = live_block = {}
    _attempt(live_block, "simbad", lambda: live.simbad_lookup(rec.get("simbad_id") or rec["name"]))
    if rec.get("pulsar"):
        _attempt(live_block, "pulsar", lambda: live.pulsar(rec["pulsar"]))
    else:
        _attempt(live_block, "pulsars_within_10arcmin", lambda: live.pulsars_near(coord, 10.0))
    _attempt(live_block, "green_snr_within_15arcmin", lambda: live.vizier_cone(coord, 15.0, "green_snr", 5))
    _attempt(live_block, "hgps_within_20arcmin", lambda: live.vizier_cone(coord, 20.0, "hgps", 5))
    if rec.get("in_cgps") or (rec.get("cgps") or {}).get("in_cgps"):
        _attempt(live_block, "cgps_products", lambda: live.cgps_products(coord))
    return out
