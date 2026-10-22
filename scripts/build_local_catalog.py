"""Regenerate the bundled catalogs (src/pwn_mcp/data/pwne.csv, nebulae.csv) from live services.

Hand-curated inputs (names, associations, PWN class) live in *_curated.csv; every number in
the outputs comes from SIMBAD, Green's SNR catalogue (VizieR VII/297), the ATNF pulsar
catalogue (via psrqpy) or the H.E.S.S. Galactic Plane Survey (VizieR J/A+A/612/A1).

    uv run python scripts/build_local_catalog.py
"""

from __future__ import annotations

import csv
import math
import sys
import warnings
from datetime import date
from pathlib import Path

import astropy.units as u
from astropy.coordinates import SkyCoord

DATA = Path(__file__).resolve().parents[1] / "src" / "pwn_mcp" / "data"
sys.path.insert(0, str(DATA.parents[1]))

from pwn_mcp.catalog.cgps import in_cgps  # noqa: E402

GREEN = "VII/297"
HGPS = "J/A+A/612/A1"
ATNF_PARAMS = ["JNAME", "BNAME", "RAJD", "DECJD", "P0", "P1", "EDOT", "AGE", "BSURF", "DIST", "DM"]


def read_curated(name: str) -> list[dict]:
    with open(DATA / name) as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def fetch_green() -> dict[str, dict]:
    from astroquery.vizier import Vizier

    table = Vizier(row_limit=-1, columns=["**"]).get_catalogs(GREEN)[0]
    out = {}
    for row in table:
        c = SkyCoord(row["RAJ2000"], row["DEJ2000"], unit=(u.hourangle, u.deg))
        maj = _num(row["MajDiam"])
        minor = _num(row["MinDiam"])
        out[str(row["SNR"])] = {
            "ra": c.ra.deg,
            "dec": c.dec.deg,
            "type": str(row["type"]),
            "maj_arcmin": maj,
            "min_arcmin": minor if minor is not None else maj,
            "flux_1ghz_jy": _num(row["S(1GHz)"]),
            "spectral_index": _num(row["Sp-Index"]),
            "names": str(row["Names"]),
        }
    return out


def fetch_pulsars(names: list[str]) -> dict[str, dict]:
    import psrqpy

    q = psrqpy.QueryATNF(params=ATNF_PARAMS, psrs=names)
    out = {}
    for row in q.table:
        out[str(row["JNAME"])] = {
            "bname": _str(row["BNAME"]),
            "ra": float(row["RAJD"]),
            "dec": float(row["DECJD"]),
            "p0_s": _num(row["P0"]),
            "p1": _num(row["P1"]),
            "edot_erg_s": _num(row["EDOT"]),
            "char_age_yr": _num(row["AGE"]),
            "bsurf_g": _num(row["BSURF"]),
            "dist_kpc": _num(row["DIST"]),
            "dm": _num(row["DM"]),
        }
    out["_version"] = str(q.get_version)
    return out


def fetch_hgps_idents() -> list[dict]:
    from astroquery.vizier import Vizier

    cats = Vizier(row_limit=-1, columns=["**"]).get_catalogs(HGPS)
    ident = next(t for t in cats if t.meta["name"].endswith("/ident"))
    srcs = next(t for t in cats if t.meta["name"].endswith("/sources"))
    pos = {str(r["Source"]): (float(r["GLON"]), float(r["GLAT"])) for r in srcs}
    return [
        {
            "source": str(r["Source"]),
            "object": str(r["IdObject"]),
            "class": str(r["Class"]),
            "glon_glat": pos.get(str(r["Source"])),
        }
        for r in ident
    ]


def simbad_position(ident: str) -> tuple[float, float] | None:
    from astroquery.simbad import Simbad

    try:
        t = Simbad.query_object(ident)
    except Exception as exc:  # pragma: no cover - network
        print(f"  SIMBAD error for {ident!r}: {exc}", file=sys.stderr)
        return None
    if t is None or len(t) == 0:
        print(f"  SIMBAD: no match for {ident!r}", file=sys.stderr)
        return None
    return float(t["ra"][0]), float(t["dec"][0])


def _num(v):
    warnings.filterwarnings("ignore", "Warning: converting a masked element to nan")
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _str(v):
    s = str(v).strip()
    return "" if s in {"", "--", "nan", "None"} else s


def _fmt(v, digits=6):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.{digits}g}"
    return str(v)


def galactic(ra: float, dec: float) -> tuple[float, float]:
    g = SkyCoord(ra * u.deg, dec * u.deg).galactic
    return g.l.deg, g.b.deg


def match_hgps(row: dict, psr: dict | None, idents: list[dict]) -> str:
    keys = {row["name"].lower()} | {a.strip().lower() for a in row["aliases"].split(";") if a.strip()}
    if row["pulsar"]:
        keys |= {f"psr {row['pulsar']}".lower()}
        if psr and psr.get("bname"):
            keys.add(f"psr {psr['bname']}".lower())
    if row["green_snr"]:
        g = row["green_snr"]
        keys.add(g.lower())
    for ident in idents:
        obj = ident["object"].lower()
        if obj in keys or any(k and k in obj for k in keys if len(k) > 6):
            return ident["source"]
    return ""


def build_pwne(green, idents) -> list[dict]:
    curated = read_curated("pwne_curated.csv")
    psrs = fetch_pulsars([r["pulsar"] for r in curated if r["pulsar"]])
    print(f"ATNF catalogue version {psrs.pop('_version')}")
    out = []
    for r in curated:
        snr = green.get(r["green_snr"]) if r["green_snr"] else None
        if r["green_snr"] and snr is None:
            print(f"  {r['name']}: {r['green_snr']} not in Green catalogue", file=sys.stderr)
        psr = psrs.get(r["pulsar"]) if r["pulsar"] else None
        if r["pulsar"] and psr is None:
            print(f"  {r['name']}: pulsar {r['pulsar']} not in ATNF", file=sys.stderr)

        pos, pos_src = None, ""
        if r["simbad_id"]:
            pos, pos_src = simbad_position(r["simbad_id"]), "SIMBAD"
        if pos is None and psr:
            pos, pos_src = (psr["ra"], psr["dec"]), "ATNF pulsar"
        if pos is None and snr:
            pos, pos_src = (snr["ra"], snr["dec"]), "Green SNR centre"
        if pos is None:
            print(f"  {r['name']}: no position; skipped", file=sys.stderr)
            continue
        l, b = galactic(*pos)
        pwn_size = snr["maj_arcmin"] if snr and snr["type"].startswith("F") else None
        out.append(
            {
                "name": r["name"],
                "aliases": r["aliases"],
                "kind": "pwn",
                "pwn_type": r["pwn_type"],
                "ra": pos[0],
                "dec": pos[1],
                "l": l,
                "b": b,
                "position_source": pos_src,
                "in_cgps": in_cgps(l, b),
                "host_snr": r["green_snr"],
                "snr_type": snr["type"] if snr else "",
                "snr_ra": snr["ra"] if snr else None,
                "snr_dec": snr["dec"] if snr else None,
                "snr_maj_arcmin": snr["maj_arcmin"] if snr else None,
                "snr_min_arcmin": snr["min_arcmin"] if snr else None,
                "pwn_size_arcmin": pwn_size,
                "radio_flux_1ghz_jy": snr["flux_1ghz_jy"] if snr else None,
                "radio_spectral_index": snr["spectral_index"] if snr else None,
                "pulsar": r["pulsar"],
                "pulsar_bname": psr["bname"] if psr else "",
                "psr_ra": psr["ra"] if psr else None,
                "psr_dec": psr["dec"] if psr else None,
                "p0_s": psr["p0_s"] if psr else None,
                "p1": psr["p1"] if psr else None,
                "edot_erg_s": psr["edot_erg_s"] if psr else None,
                "char_age_yr": psr["char_age_yr"] if psr else None,
                "bsurf_g": psr["bsurf_g"] if psr else None,
                "dist_kpc": psr["dist_kpc"] if psr else None,
                "tev_source": match_hgps(r, psr, idents),
                "color_template": r["color_template"],
                "notes": r["notes"],
            }
        )
    return out


def build_nebulae(green) -> list[dict]:
    out = []
    for r in read_curated("nebulae_curated.csv"):
        snr = green.get(r["green_snr"]) if r["green_snr"] else None
        pos, src = simbad_position(r["simbad_id"]), "SIMBAD"
        if pos is None and snr:
            pos, src = (snr["ra"], snr["dec"]), "Green SNR centre"
        if pos is None:
            print(f"  {r['name']}: no position; skipped", file=sys.stderr)
            continue
        l, b = galactic(*pos)
        out.append(
            {
                "name": r["name"],
                "aliases": r["aliases"],
                "kind": r["kind"],
                "ra": pos[0],
                "dec": pos[1],
                "l": l,
                "b": b,
                "position_source": src,
                "in_cgps": in_cgps(l, b),
                "green_snr": r["green_snr"],
                "snr_type": snr["type"] if snr else "",
                "size_arcmin": snr["maj_arcmin"] if snr else None,
                "color_template": r["color_template"],
                "notes": r["notes"],
            }
        )
    return out


def write(name: str, rows: list[dict], sources: str) -> None:
    path = DATA / name
    with open(path, "w", newline="") as f:
        f.write(f"# Generated by scripts/build_local_catalog.py on {date.today()} from {sources}\n")
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for row in rows:
            w.writerow({k: _fmt(v) for k, v in row.items()})
    print(f"wrote {len(rows)} rows to {path}")


def main() -> None:
    green = fetch_green()
    print(f"Green catalogue: {len(green)} SNRs")
    idents = fetch_hgps_idents()
    write(
        "pwne.csv",
        build_pwne(green, idents),
        f"SIMBAD, VizieR {GREEN} (Green), ATNF pulsar catalogue, VizieR {HGPS} (HGPS)",
    )
    write("nebulae.csv", build_nebulae(green), f"SIMBAD, VizieR {GREEN} (Green)")


if __name__ == "__main__":
    main()
