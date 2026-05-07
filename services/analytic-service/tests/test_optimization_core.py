"""
Unit tests for the pure optimization functions (_model, _cost, _optimize_scipy, _optimize_grid).
These tests do not need the FastAPI app or a database — they test math only.
"""

import pytest
from app.main import OptimizationIn, _model, _cost, _optimize_scipy, _optimize_grid, _build_result


def default_req(**overrides) -> OptimizationIn:
    data = dict(
        method="scipy",
        fan_power_kw=15.0,
        energy_cost_kwh=0.12,
        radiation_limit=20.0,
        pressure_target=-120.0,
        airflow_min=5000.0,
        airflow_max=40000.0,
        filter_efficiency=0.999,
        current_radiation=10.0,
    )
    data.update(overrides)
    return OptimizationIn(**data)


class TestModel:
    def test_radiation_decreases_with_higher_airflow(self):
        req = default_req()
        r_low = _model(5000, 0.5, req)["radiation"]
        r_high = _model(40000, 0.5, req)["radiation"]
        assert r_high < r_low

    def test_pressure_decreases_with_higher_fan_load(self):
        req = default_req()
        p_low = _model(10000, 0.1, req)["pressure"]
        p_high = _model(10000, 1.0, req)["pressure"]
        assert p_high < p_low

    def test_pressure_formula(self):
        req = default_req()
        result = _model(20000, 0.5, req)
        assert result["pressure"] == pytest.approx(-50.0 - 200.0 * 0.5, rel=1e-6)

    def test_energy_formula(self):
        req = default_req()
        result = _model(20000, 0.8, req)
        expected_energy = 15.0 * (0.8**2 + 0.1)
        assert result["energy"] == pytest.approx(expected_energy, rel=1e-6)

    def test_energy_increases_with_fan_load(self):
        req = default_req()
        e_low = _model(20000, 0.1, req)["energy"]
        e_high = _model(20000, 0.9, req)["energy"]
        assert e_high > e_low

    def test_full_filter_efficiency_reduces_radiation_to_near_zero(self):
        req = default_req(filter_efficiency=1.0, current_radiation=10.0)
        result = _model(40000, 0.5, req)
        assert result["radiation"] == pytest.approx(0.0, abs=0.1)

    def test_zero_filter_efficiency_leaves_radiation_unchanged(self):
        req = default_req(filter_efficiency=0.0, current_radiation=10.0)
        result = _model(40000, 0.5, req)
        assert result["radiation"] == pytest.approx(10.0, rel=1e-6)


class TestCostFunction:
    def test_cost_is_positive(self):
        req = default_req()
        c = _cost(20000, 0.5, req)
        assert c > 0

    def test_radiation_penalty_activates_above_limit(self):
        req = default_req(radiation_limit=1.0, current_radiation=100.0, filter_efficiency=0.0)
        c_with_penalty = _cost(20000, 0.5, req)
        req2 = default_req(radiation_limit=1000.0, current_radiation=100.0, filter_efficiency=0.0)
        c_without_penalty = _cost(20000, 0.5, req2)
        assert c_with_penalty > c_without_penalty

    def test_airflow_below_min_adds_penalty(self):
        req = default_req(airflow_min=10000.0)
        c_inside = _cost(10000, 0.5, req)
        c_outside = _cost(1000, 0.5, req)
        assert c_outside > c_inside

    def test_airflow_above_max_adds_penalty(self):
        req = default_req(airflow_max=30000.0)
        c_inside = _cost(30000, 0.5, req)
        c_outside = _cost(50000, 0.5, req)
        assert c_outside > c_inside

    def test_energy_cost_increases_with_fan_load(self):
        req = default_req()
        c_low = _cost(20000, 0.1, req)
        c_high = _cost(20000, 0.9, req)
        assert c_high > c_low


class TestOptimizeScipy:
    def test_returns_valid_result_structure(self):
        req = default_req()
        result = _optimize_scipy(req)
        assert "method" in result
        assert "optimal_airflow" in result
        assert "optimal_fan_load" in result
        assert "expected_radiation" in result
        assert "expected_pressure" in result
        assert "energy_kw" in result
        assert "energy_cost_per_hour" in result
        assert "safety_margin" in result
        assert "status" in result
        assert "iterations" in result

    def test_optimal_airflow_within_bounds(self):
        req = default_req()
        result = _optimize_scipy(req)
        assert req.airflow_min <= result["optimal_airflow"] <= req.airflow_max

    def test_optimal_fan_load_within_bounds(self):
        req = default_req()
        result = _optimize_scipy(req)
        assert 0.05 <= result["optimal_fan_load"] <= 1.0

    def test_method_field_is_scipy(self):
        req = default_req(method="scipy")
        result = _optimize_scipy(req)
        assert result["method"] == "scipy"

    def test_safety_margin_positive_for_safe_radiation(self):
        req = default_req(current_radiation=5.0, radiation_limit=20.0)
        result = _optimize_scipy(req)
        assert result["safety_margin"] > 0

    def test_radiation_below_limit(self):
        req = default_req(current_radiation=5.0, radiation_limit=20.0)
        result = _optimize_scipy(req)
        assert result["expected_radiation"] < req.radiation_limit


class TestOptimizeGrid:
    def test_returns_valid_result_structure(self):
        req = default_req(method="grid")
        result = _optimize_grid(req)
        assert "optimal_airflow" in result
        assert "optimal_fan_load" in result
        assert result["status"] == "ok"

    def test_iterations_equal_500(self):
        req = default_req(method="grid")
        result = _optimize_grid(req)
        assert result["iterations"] == 500  # 25 * 20

    def test_optimal_airflow_within_bounds(self):
        req = default_req(method="grid")
        result = _optimize_grid(req)
        assert req.airflow_min <= result["optimal_airflow"] <= req.airflow_max

    def test_grid_and_scipy_give_similar_results(self):
        req = default_req()
        scipy_result = _optimize_scipy(req)
        grid_result = _optimize_grid(req)
        # Cost functions should be in the same ballpark (within 20%)
        scipy_cost = _cost(scipy_result["optimal_airflow"], scipy_result["optimal_fan_load"], req)
        grid_cost = _cost(grid_result["optimal_airflow"], grid_result["optimal_fan_load"], req)
        assert abs(scipy_cost - grid_cost) / max(scipy_cost, grid_cost) < 0.2
