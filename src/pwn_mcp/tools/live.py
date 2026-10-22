"""Live catalog tools: cone searches, VizieR tables, ATNF pulsars."""

from __future__ import annotations

from typing import Annotated, Literal

import astropy.units as u
from astropy.coordinates import SkyCoord
from mcp.server.mcpserver import MCPServer
from pydantic import Field

from ..catalog import live, local
from ..catalog.sources import VIZIER_SOURCES
from .catalog import resolve_position, summarize

CatalogKey = Literal["green_snr", "hgps", "sharpless", "wise_hii", "strasbourg_pn"]


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    def list_catalogs() -> dict:
        """Catalogs available to cone_search and query_vizier, plus the bundled tables."""
        return {
            "vizier": {
                k: {"table": s.table, "title": s.title, "kind": s.kind, "reference": s.reference}
                for k, s in VIZIER_SOURCES.items()
            },
            "other": {
                "atnf": "ATNF pulsar catalogue (Manchester et al. 2005, AJ 129, 1993) via psrqpy",
                "simbad": "SIMBAD name resolution and object types",
                "cadc_cgps": "Canadian Galactic Plane Survey products at CADC",
            },
            "bundled": local.provenance(),
        }

    @mcp.tool()
    def cone_search(
        name: str | None = None,
        ra: float | None = None,
        dec: float | None = None,
        l: float | None = None,
        b: float | None = None,
        radius_arcmin: Annotated[float, Field(gt=0, le=600)] = 30.0,
        catalogs: tuple[CatalogKey | Literal["atnf", "bundled"], ...] = (
            "bundled",
            "green_snr",
            "hgps",
            "atnf",
        ),
        limit: Annotated[int, Field(ge=1, le=500)] = 25,
    ) -> dict:
        """Find catalogued SNRs, TeV sources, H II regions, PNe and pulsars around a position or
        named object."""
        coord, _ = resolve_position(name, ra, dec, l, b)
        g = coord.galactic
        out: dict = {
            "center": {"ra": coord.ra.deg, "dec": coord.dec.deg, "l": g.l.deg, "b": g.b.deg},
            "radius_arcmin": radius_arcmin,
            "results": {},
            "errors": {},
        }
        for cat in catalogs:
            try:
                if cat == "bundled":
                    hits = []
                    for rec in local.records():
                        sep = coord.separation(SkyCoord(rec["ra"] * u.deg, rec["dec"] * u.deg)).arcmin
                        if sep <= radius_arcmin:
                            hits.append({**summarize(rec), "sep_arcmin": round(float(sep), 3)})
                    out["results"][cat] = sorted(hits, key=lambda r: r["sep_arcmin"])[:limit]
                elif cat == "atnf":
                    out["results"][cat] = live.pulsars_near(coord, radius_arcmin)[:limit]
                else:
                    out["results"][cat] = live.vizier_cone(coord, radius_arcmin, cat, limit)
            except Exception as exc:
                out["errors"][cat] = f"{type(exc).__name__}: {exc}"
        if not out["errors"]:
            del out["errors"]
        return out

    @mcp.tool()
    def query_vizier(
        catalog: CatalogKey,
        constraints: Annotated[
            dict[str, str] | None,
            Field(
                description="VizieR column constraints, e.g. {'type': 'F'} or {'type': 'C*'} on green_snr."
            ),
        ] = None,
        limit: Annotated[int, Field(ge=1, le=5000)] = 500,
    ) -> dict:
        """Query a whole VizieR catalog with optional column constraints, e.g. all filled-centre
        (type F) or composite (type C) remnants in Green's SNR catalogue."""
        rows = live.vizier_table(catalog, constraints, limit)
        return {"catalog": VIZIER_SOURCES[catalog].title, "count": len(rows), "rows": rows}

    @mcp.tool()
    def get_pulsar(
        name: Annotated[str, Field(description="PSR J or B name, e.g. J0534+2200 or B0531+21.")],
    ) -> dict:
        """ATNF pulsar catalogue parameters: period, Ṗ, spin-down power Ė, characteristic age,
        surface and light-cylinder fields, DM and distance, associations."""
        rec = live.pulsar(name)
        if rec is None:
            raise ValueError(f"Pulsar {name!r} not found in the ATNF catalogue.")
        return rec
