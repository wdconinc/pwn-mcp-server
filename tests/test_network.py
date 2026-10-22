"""Tests that contact remote services. Run with: uv run pytest -m network"""

import os

import astropy.units as u
import pytest
from astropy.coordinates import SkyCoord

pytestmark = pytest.mark.network


@pytest.fixture(autouse=True)
def online(monkeypatch):
    from pwn_mcp import config

    monkeypatch.setattr(config, "OFFLINE", False)
    yield


def test_simbad():
    from pwn_mcp.catalog import live

    hit = live.simbad_lookup("Crab Nebula")
    assert hit and abs(hit["ra"] - 83.63) < 0.1


def test_atnf():
    from pwn_mcp.catalog import live

    assert live.pulsar("J0534+2200")["bname"] == "B0531+21"


def test_green_cone():
    from pwn_mcp.catalog import live

    rows = live.vizier_cone(SkyCoord(l=29.7 * u.deg, b=-0.24 * u.deg, frame="galactic"), 10, "green_snr")
    assert rows[0]["name"] == "G029.7-00.3"


def test_cadc_cgps():
    from pwn_mcp.catalog import live

    products = live.cgps_products(SkyCoord(l=54.1 * u.deg, b=0.27 * u.deg, frame="galactic"))
    assert any(p["product_id"] == "1420MHz" for p in products)


def test_offline_flag_blocks(monkeypatch):
    from pwn_mcp import config
    from pwn_mcp.catalog import live

    monkeypatch.setattr(config, "OFFLINE", True)
    with pytest.raises(live.OfflineError):
        live.simbad_lookup(f"uncached-{os.getpid()}")
