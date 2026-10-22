"""Fetch image cutouts: CGPS mosaics from CADC, everything else through CDS hips2fits."""

from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS

from .. import config
from ..catalog.live import require_online
from .surveys import Survey

warnings.filterwarnings("ignore", category=u.UnitsWarning)
warnings.filterwarnings("ignore", module="astropy.wcs")


@dataclass
class Cutout:
    data: np.ndarray  # (ny, nx) or (ny, nx, 3) for RGB
    wcs: WCS
    survey: Survey
    backend: str
    origin: str  # observation id / HiPS id
    unit: str = ""


def _cache_path(key: str, suffix: str):
    return config.cache_dir("images") / (hashlib.sha256(key.encode()).hexdigest()[:24] + suffix)


def make_wcs(center: SkyCoord, fov_deg: float, npix: int, frame: str = "galactic") -> WCS:
    w = WCS(naxis=2)
    if frame == "galactic":
        g = center.galactic
        w.wcs.ctype = ["GLON-TAN", "GLAT-TAN"]
        w.wcs.crval = [g.l.deg, g.b.deg]
    else:
        w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        w.wcs.crval = [center.icrs.ra.deg, center.icrs.dec.deg]
    scale = fov_deg / npix
    w.wcs.cdelt = [-scale, scale]
    w.wcs.crpix = [npix / 2 + 0.5, npix / 2 + 0.5]
    w.pixel_shape = (npix, npix)
    return w


def hips_cutout(
    survey: Survey, center: SkyCoord, fov_deg: float, npix: int = 600, frame: str = "galactic"
) -> Cutout:
    wcs = make_wcs(center, fov_deg, npix, frame)
    key = f"hips:{survey.hips_id}:{wcs.wcs.crval}:{fov_deg}:{npix}:{frame}:{survey.rgb}"
    path = _cache_path(key, ".npy")
    if path.exists():
        data = np.load(path)
    else:
        require_online()
        from astroquery.hips2fits import hips2fits

        if survey.rgb:
            data = np.asarray(hips2fits.query_with_wcs(hips=survey.hips_id, wcs=wcs, format="png"))
            data = data[::-1, :, :3]  # PNG rows run top-down; FITS/WCS rows bottom-up
        else:
            hdul = hips2fits.query_with_wcs(hips=survey.hips_id, wcs=wcs, format="fits")
            data = np.asarray(hdul[0].data, dtype=float)
        np.save(path, data)
    return Cutout(data, wcs, survey, "hips2fits", survey.hips_id, survey.unit)


def cadc_cgps_cutout(survey: Survey, center: SkyCoord, fov_deg: float) -> Cutout:
    """Cutout from the CGPS mosaic(s) covering ``center``; picks the mosaic with most valid pixels."""
    radius = fov_deg / 2 * np.sqrt(2)
    key = f"cadc:{survey.cadc_product}:{center.icrs.ra.deg:.5f}:{center.icrs.dec.deg:.5f}:{radius:.4f}"
    path = _cache_path(key, ".fits")
    if not path.exists():
        require_online()
        from astroquery.cadc import Cadc

        cadc = Cadc()
        table = cadc.query_region(center, radius=0.05 * u.deg, collection="CGPS")
        table = table[table["productID"] == survey.cadc_product]
        if len(table) == 0:
            raise LookupError(f"No CGPS {survey.cadc_product} mosaic covers this position.")
        best, best_n, best_obs = None, -1, ""
        for i in range(min(len(table), 4)):
            url = cadc.get_image_list(table[i : i + 1], center, radius * u.deg)[0]
            with fits.open(url, cache=False) as hdul:
                hdu = hdul[0].copy()
            n = int(np.isfinite(hdu.data).sum())
            if n > best_n:
                best, best_n, best_obs = hdu, n, str(table["observationID"][i])
        best.header["PWNOBSID"] = best_obs
        best.writeto(path, overwrite=True)
    with fits.open(path) as hdul:
        hdr = hdul[0].header
        data = np.squeeze(np.asarray(hdul[0].data, dtype=float))
        wcs = WCS(hdr).celestial
        return Cutout(data, wcs, survey, "CADC", hdr.get("PWNOBSID", ""), hdr.get("BUNIT", survey.unit))


def fetch(
    survey: Survey, center: SkyCoord, fov_deg: float, npix: int = 600, frame: str = "galactic"
) -> Cutout:
    if survey.backend == "cadc":
        try:
            return cadc_cgps_cutout(survey, center, fov_deg)
        except LookupError:
            raise
        except Exception:
            if survey.hips_id is None:
                raise
            # Fall back to the HiPS rendering of the same survey.
    return hips_cutout(survey, center, fov_deg, npix, frame)
