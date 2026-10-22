import numpy as np
import pytest

from pwn_mcp.color import colorimetry as c
from pwn_mcp.color import spectra as s
from pwn_mcp.color.observers import white_point_xy


@pytest.mark.parametrize("observer", ["cie1931_2", "cie1964_10"])
def test_equal_energy_is_one_third(observer):
    xy = c.observer_color(s.equal_energy(), observer).xy
    assert xy == pytest.approx([1 / 3, 1 / 3], abs=2e-4)


def test_monochromatic_500nm_matches_cie1931_table():
    # CIE 1931 2° spectral chromaticity at 500 nm: x = 0.0082, y = 0.5384
    spec = s.emission_lines({500.0: 1.0}, fwhm_kms=1.0)
    assert c.observer_color(spec, "cie1931_2").xy == pytest.approx([0.0082, 0.5384], abs=2e-3)


def test_d65_white_points():
    assert white_point_xy("cie1931_2") == pytest.approx([0.3127, 0.3290], abs=1e-4)
    assert white_point_xy("cie1964_10") == pytest.approx([0.3138, 0.3310], abs=1e-4)


def test_halpha_red_and_oiii_teal():
    ha = c.observer_color(s.template_spectrum("h_alpha_only"), "cie1931_2")
    oiii = c.observer_color(s.template_spectrum("oiii_only"), "cie1931_2")
    assert ha.dominant_wavelength_nm == pytest.approx(656, abs=1)
    assert oiii.dominant_wavelength_nm == pytest.approx(501, abs=1)
    r, g, b = (int(ha.srgb_hex[i:i + 2], 16) for i in (1, 3, 5))
    assert r == 255 and g < 40
    r, g, b = (int(oiii.srgb_hex[i:i + 2], 16) for i in (1, 3, 5))
    assert r < 40 and g > 200 and b > 150


def test_observers_differ_but_boundedly():
    for key in ("hii_region", "planetary_nebula", "crab_composite"):
        d = c.compare_observers(s.template_spectrum(key))["differences"][0]
        assert 1e-4 < d["delta_uv_prime"] < 0.1
        assert d["delta_E2000"] > 0


def test_scotopic_ratio_rod_blind_to_halpha():
    assert c.scotopic_ratio(s.template_spectrum("h_alpha_only"))["s_over_p"] < 0.05
    assert c.scotopic_ratio(s.template_spectrum("oiii_only"))["s_over_p"] > 5


def test_reddening_shifts_red():
    blue = c.observer_color(s.template_spectrum("crab_synchrotron"), "cie1931_2").xy
    red = c.observer_color(s.template_spectrum("crab_synchrotron", ebv=0.52), "cie1931_2").xy
    assert red[0] > blue[0]


def test_ccm89_normalization():
    a = s.ccm89_a_lambda(np.array([440.0, 549.0]))
    assert a[1] == pytest.approx(1.0, abs=0.01)
    assert a[0] == pytest.approx(1.32, abs=0.03)


def test_line_lookup():
    assert s.resolve_line("OIII_5007") == pytest.approx(500.68)
    assert s.resolve_line("[O III] 5007") == pytest.approx(500.68)
    assert s.resolve_line(656.3) == 656.3
    with pytest.raises(ValueError):
        s.resolve_line("nonsense")
