"""Catalog tools: search and look up PWNe and other nebulae; CGPS coverage."""

from __future__ import annotations

from typing import Annotated, Literal

import astropy.units as u
from astropy.coordinates import SkyCoord
from mcp.server.mcpserver import MCPServer
from pydantic import Field

from ..catalog import cgps, local
from . import tool

Kind = Literal["pwn", "snr", "hii", "pn"]
PwnType = Literal["filled-center", "composite", "relic", "bow-shock"]

SUMMARY_FIELDS = (
    "name",
    "kind",
    "pwn_type",
    "l",
    "b",
    "ra",
    "dec",
    "in_cgps",
    "host_snr",
    "pulsar",
    "edot_erg_s",
    "char_age_yr",
    "dist_kpc",
    "tev_source",
    "source",
)


def summarize(rec: dict) -> dict:
    return {k: rec[k] for k in SUMMARY_FIELDS if rec.get(k) not in (None, "", [])}


def resolve_position(
    name: str | None, ra: float | None, dec: float | None, l: float | None, b: float | None
) -> tuple[SkyCoord, dict | None]:
    """Turn a name or coordinates into a SkyCoord; bundled catalog first, then SIMBAD."""
    if ra is not None and dec is not None:
        return SkyCoord(ra * u.deg, dec * u.deg), None
    if l is not None and b is not None:
        return SkyCoord(l=l * u.deg, b=b * u.deg, frame="galactic").icrs, None
    if not name:
        raise ValueError("Give a name, or ra/dec, or l/b.")
    rec = local.find(name)
    if rec:
        return SkyCoord(rec["ra"] * u.deg, rec["dec"] * u.deg), rec
    from ..catalog import live

    hit = live.simbad_lookup(name)
    if not hit:
        raise ValueError(f"Could not resolve {name!r} in the bundled catalog or SIMBAD.")
    return SkyCoord(hit["ra"] * u.deg, hit["dec"] * u.deg), hit


def register(mcp: MCPServer) -> None:
    @tool(mcp)
    def search_nebulae(
        query: Annotated[
            str | None, Field(description="Substring of a name, alias, SNR, pulsar or TeV id.")
        ] = None,
        kind: Annotated[Kind | None, Field(description="pwn, snr, hii (H II region) or pn.")] = None,
        pwn_type: PwnType | None = None,
        l_min: Annotated[
            float | None, Field(description="Galactic longitude range (deg); wraps if l_min > l_max.")
        ] = None,
        l_max: float | None = None,
        b_min: float | None = None,
        b_max: float | None = None,
        in_cgps: Annotated[bool | None, Field(description="Inside the CGPS 1420 MHz footprint.")] = None,
        has_pulsar: bool | None = None,
        min_edot: Annotated[
            float | None, Field(description="Minimum pulsar spin-down power (erg/s).")
        ] = None,
        limit: Annotated[int, Field(ge=1, le=500)] = 50,
    ) -> dict:
        """Search the bundled catalog of pulsar wind nebulae and showcase nebulae (SNRs, H II
        regions, planetary nebulae) by name, type, Galactic position, CGPS coverage or pulsar
        properties. Use cone_search or query_vizier for the full live catalogs."""
        hits = local.search(
            query, kind, pwn_type, l_min, l_max, b_min, b_max, in_cgps, has_pulsar, min_edot, limit
        )
        return {"count": len(hits), "results": [summarize(h) for h in hits], "provenance": local.provenance()}

    @tool(mcp)
    def get_nebula(
        name: Annotated[
            str, Field(description="Name, alias, Green SNR id (e.g. G21.5-0.9), PSR J name or HGPS id.")
        ],
        live: Annotated[bool, Field(description="Also query SIMBAD/VizieR/ATNF for extra detail.")] = False,
    ) -> dict:
        """Full record for one nebula: position, PWN class, host SNR (Green catalogue), powering
        pulsar (ATNF: P, Ṗ, Ė, τ_c, B, distance), TeV counterpart (HGPS), CGPS coverage and the
        matching colour template. Unknown names fall back to SIMBAD."""
        rec = local.find(name)
        if rec is None:
            from ..catalog import live as live_mod

            rec = live_mod.simbad_lookup(name)
            if rec is None:
                raise ValueError(f"{name!r} not found in the bundled catalog or SIMBAD.")
            live = False
        rec = dict(rec)
        rec["cgps"] = cgps.coverage(rec["l"], rec["b"])
        if live:
            from ..catalog import merge

            rec = merge.enrich(rec)
        return rec

    @tool(mcp)
    def cgps_coverage(
        name: str | None = None,
        ra: float | None = None,
        dec: float | None = None,
        l: float | None = None,
        b: float | None = None,
        query_archive: Annotated[
            bool, Field(description="Also list CGPS products at CADC (network).")
        ] = False,
    ) -> dict:
        """Is a position or named object inside the Canadian Galactic Plane Survey (1420 MHz,
        408 MHz, HI)? Optionally list the actual CGPS data products at CADC."""
        coord, _ = resolve_position(name, ra, dec, l, b)
        g = coord.galactic
        out = cgps.coverage(g.l.deg, g.b.deg)
        if name:
            out["name"] = name
        if query_archive:
            from ..catalog import live

            out["cadc_products"] = live.cgps_products(coord)
        return out
