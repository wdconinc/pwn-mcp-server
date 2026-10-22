import json

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord

from pwn_mcp.catalog import local
from pwn_mcp.imaging import fetch, render
from pwn_mcp.imaging.surveys import SURVEYS, get_survey
from pwn_mcp.plotting import save_figure


def synthetic_cutout(center, fov_deg, npix=120):
    wcs = fetch.make_wcs(center, fov_deg, npix)
    y, x = np.mgrid[:npix, :npix]
    data = np.exp(-((x - npix / 2) ** 2 + (y - npix / 2) ** 2) / (2 * (npix / 10) ** 2))
    data[:5, :5] = np.nan
    return fetch.Cutout(data, wcs, get_survey("cgps_1420"), "synthetic", "test", "K (Tb)")


def test_make_wcs_centers_target():
    c = SkyCoord(l=54.1 * u.deg, b=0.27 * u.deg, frame="galactic")
    w = fetch.make_wcs(c, 0.5, 200)
    x, y = w.world_to_pixel(c)
    assert abs(x - 99.5) < 1e-6 and abs(y - 99.5) < 1e-6


def test_render_with_overlays_offline():
    rec = local.find("G54.1+0.3")
    center = SkyCoord(rec["ra"] * u.deg, rec["dec"] * u.deg)
    cut = synthetic_cutout(center, 0.4)
    fig = render.render_cutout(cut, center, 0.4, "test", rec)
    png, path = save_figure(fig, "test_cutout")
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and path.exists()


def test_panels_with_missing_survey():
    center = SkyCoord(l=130.7 * u.deg, b=3.1 * u.deg, frame="galactic")
    panels = [(synthetic_cutout(center, 0.3), "ok"), (None, "unavailable: offline")]
    fig = render.render_panels(panels, center, 0.3, "test", None, ("pulsar",))
    assert len(fig.axes) >= 2


def test_survey_registry():
    assert SURVEYS["cgps_1420"].backend == "cadc"
    assert all(s.hips_id or s.cadc_product for s in SURVEYS.values())


def test_cutout_tool_offline_reports_error():
    from tests.test_server import call

    result = call("render_cutout", {"name": "G54.1+0.3", "survey": "nvss"})
    assert result.is_error and "offline" in result.content[0].text.lower()
    surveys = json.loads(call("list_surveys").content[0].text)["surveys"]
    assert any(s["key"] == "cgps_1420" for s in surveys)
