import pytest

from pwn_mcp.catalog import cgps, local


def test_bundled_catalog_loads():
    recs = local.records()
    assert sum(r["kind"] == "pwn" for r in recs) >= 30
    assert {r["kind"] for r in recs} == {"pwn", "snr", "hii", "pn"}
    for r in recs:
        assert -90 <= r["dec"] <= 90 and 0 <= r["l"] < 360


@pytest.mark.parametrize(
    "name", ["Crab Nebula", "M1", "crab nebula", "G184.6-5.8", "PSR J0534+2200", "B0531+21", "G184.6-05.8"]
)
def test_find_by_any_name(name):
    assert local.find(name)["name"] == "Crab Nebula"


def test_galactic_name_normalization():
    assert local.normalize_name("G21.5-0.9") == local.normalize_name("G021.5-00.9")
    assert local.find("G21.5-0.9")["pulsar"] == "J1833-1034"


def test_search_filters():
    cgps_pwne = local.search(kind="pwn", in_cgps=True)
    assert cgps_pwne and all(52 <= r["l"] <= 192 for r in cgps_pwne)
    assert {r["name"] for r in cgps_pwne} >= {"3C 58", "G54.1+0.3", "DA 495", "G141.2+5.0"}
    bows = local.search(pwn_type="bow-shock")
    assert bows and all(r["pwn_type"] == "bow-shock" for r in bows)
    energetic = local.search(min_edot=1e38)
    assert {r["name"] for r in energetic} >= {"Crab Nebula"}
    wrap = local.search(l_min=350, l_max=10)
    assert wrap and all(r["l"] >= 350 or r["l"] <= 10 for r in wrap)


def test_cgps_footprint():
    # 3C 58 and G54.1+0.3 lie in the 1420 MHz survey; Vela and the Crab (b = -5.8) do not,
    # though the Crab is inside the wider 408 MHz coverage.
    assert cgps.in_cgps(130.7, 3.1)
    assert cgps.in_cgps(54.1, 0.3)
    assert not cgps.in_cgps(263.6, -2.8)
    assert not cgps.in_cgps(184.6, -5.8)
    assert cgps.in_cgps(184.6, -5.8, band="408 MHz")
    assert cgps.in_cgps(110.0, 15.0)  # high-latitude extension
