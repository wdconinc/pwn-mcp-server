"""Bundled catalog of PWNe and showcase nebulae (see scripts/build_local_catalog.py)."""

from __future__ import annotations

import csv
import re
from functools import cache
from importlib.resources import files

FLOAT_FIELDS = {
    "ra",
    "dec",
    "l",
    "b",
    "snr_ra",
    "snr_dec",
    "snr_maj_arcmin",
    "snr_min_arcmin",
    "pwn_size_arcmin",
    "radio_flux_1ghz_jy",
    "radio_spectral_index",
    "psr_ra",
    "psr_dec",
    "p0_s",
    "p1",
    "edot_erg_s",
    "char_age_yr",
    "bsurf_g",
    "dist_kpc",
    "size_arcmin",
}
BOOL_FIELDS = {"in_cgps"}
KINDS = ("pwn", "snr", "hii", "pn")
PWN_TYPES = ("filled-center", "composite", "relic", "bow-shock")


def _parse(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if k in FLOAT_FIELDS:
            out[k] = float(v) if v not in ("", None) else None
        elif k in BOOL_FIELDS:
            out[k] = v == "True"
        elif k == "aliases":
            out[k] = [a.strip() for a in v.split(";") if a.strip()]
        else:
            out[k] = v
    out["source"] = "bundled"
    return out


def _read(name: str) -> list[dict]:
    text = files("pwn_mcp.data").joinpath(name).read_text()
    return [_parse(r) for r in csv.DictReader(line for line in text.splitlines() if not line.startswith("#"))]


@cache
def records() -> tuple[dict, ...]:
    return tuple(_read("pwne.csv") + _read("nebulae.csv"))


def provenance() -> dict[str, str]:
    out = {}
    for name in ("pwne.csv", "nebulae.csv"):
        first = files("pwn_mcp.data").joinpath(name).read_text().splitlines()[0]
        out[name] = first.lstrip("# ").strip()
    return out


_GALNAME = re.compile(r"^G?\s*(\d{1,3}(?:\.\d+)?)\s*([+-])\s*(\d{1,2}(?:\.\d+)?)$", re.I)


def normalize_name(name: str) -> str:
    """Canonical form for matching: Galactic names become 'G<l>±<b>' with one decimal, others
    lower-cased with spaces, hyphens and the prefixes 'PSR', 'SNR' removed."""
    s = name.strip()
    s = re.sub(r"^(psr|snr|pwn)\s+", "", s, flags=re.I)
    m = _GALNAME.match(s)
    if m:
        return f"g{float(m.group(1)):.1f}{m.group(2)}{float(m.group(3)):.1f}"
    return re.sub(r"[\s\-_'’.]", "", s.lower())


def _names(rec: dict) -> set[str]:
    names = {rec["name"], *rec.get("aliases", [])}
    for key in ("host_snr", "green_snr", "pulsar", "pulsar_bname", "tev_source"):
        if rec.get(key):
            names.add(rec[key])
    if rec.get("pulsar"):
        names.add("J" + rec["pulsar"].lstrip("J"))
    return {normalize_name(n) for n in names}


def find(name: str) -> dict | None:
    """Exact (normalized) match on name, alias, host SNR, pulsar or TeV source."""
    key = normalize_name(name)
    for rec in records():
        if key in _names(rec):
            return dict(rec)
    return None


def search(
    query: str | None = None,
    kind: str | None = None,
    pwn_type: str | None = None,
    l_min: float | None = None,
    l_max: float | None = None,
    b_min: float | None = None,
    b_max: float | None = None,
    in_cgps: bool | None = None,
    has_pulsar: bool | None = None,
    min_edot: float | None = None,
    limit: int = 50,
) -> list[dict]:
    q = normalize_name(query) if query else None
    out = []
    for rec in records():
        if kind and rec["kind"] != kind:
            continue
        if pwn_type and rec.get("pwn_type") != pwn_type:
            continue
        if q and not any(q in n for n in _names(rec)) and q not in rec.get("notes", "").lower():
            continue
        l, b = rec["l"] % 360, rec["b"]
        if l_min is not None and l_max is not None:
            inside = l_min <= l <= l_max if l_min <= l_max else (l >= l_min or l <= l_max)
            if not inside:
                continue
        elif (l_min is not None and l < l_min) or (l_max is not None and l > l_max):
            continue
        if (b_min is not None and b < b_min) or (b_max is not None and b > b_max):
            continue
        if in_cgps is not None and rec["in_cgps"] != in_cgps:
            continue
        if has_pulsar is not None and bool(rec.get("pulsar")) != has_pulsar:
            continue
        if min_edot is not None and (rec.get("edot_erg_s") or 0) < min_edot:
            continue
        out.append(dict(rec))
        if len(out) >= limit:
            break
    return out
