import pytest

from olist_ba.stats import haversine_km, wilson_ci


def test_haversine_sao_paulo_to_rio():
    # city centres ~357 km apart
    assert haversine_km(-23.5505, -46.6333, -22.9068, -43.1729) == pytest.approx(357, abs=5)


def test_wilson_ci_known_value():
    lo, hi = wilson_ci(10, 100)
    assert lo == pytest.approx(0.0552, abs=1e-4) and hi == pytest.approx(0.1744, abs=1e-4)


def test_wilson_ci_bounds():
    lo, hi = wilson_ci(0, 50)
    assert lo == pytest.approx(0, abs=1e-9) and 0 < hi < 0.1
