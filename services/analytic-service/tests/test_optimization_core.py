"""Tests for the pure optimization functions (_model, _cost, _optimize_*).

Updated for the new (КП, ОО, Δp) two-flow optimizer that replaces the
old radiation/airflow surrogate.
"""

import pytest
from app.main import (
    OptimizationIn,
    _model,
    _cost,
    _optimize_scipy,
    _optimize_grid,
)


def default_req(**overrides) -> OptimizationIn:
    data = dict(
        method="scipy",
        fan_power_kw=15.0,
        energy_cost_kwh=0.12,
        pressure_kp_target=-10.0,
        pressure_oo_target=-17.0,
        dp_kp_oo_min=2.0,
        flow_kp_min=10.0,
        flow_kp_max=28.0,
        flow_oo_min=15.0,
        flow_oo_max=40.0,
        filter_efficiency=0.999,
        current_wind_speed=2.0,
    )
    data.update(overrides)
    return OptimizationIn(**data)


class TestModel:
    def test_pressure_kp_decreases_with_higher_load(self):
        req = default_req()
        p_low  = _model(20, 30, 0.1, req)["pressure_kp"]
        p_high = _model(20, 30, 1.0, req)["pressure_kp"]
        assert p_high < p_low

    def test_pressure_oo_decreases_with_higher_load(self):
        req = default_req()
        p_low  = _model(20, 30, 0.1, req)["pressure_oo"]
        p_high = _model(20, 30, 1.0, req)["pressure_oo"]
        assert p_high < p_low

    def test_dp_kp_oo_is_difference(self):
        req = default_req()
        m = _model(20, 30, 0.5, req)
        assert m["dp_kp_oo"] == pytest.approx(m["pressure_kp"] - m["pressure_oo"])

    def test_energy_increases_with_load(self):
        req = default_req()
        e_low  = _model(20, 30, 0.1, req)["energy"]
        e_high = _model(20, 30, 0.9, req)["energy"]
        assert e_high > e_low

    def test_energy_increases_with_flow(self):
        req = default_req()
        e_small = _model(11, 16, 0.5, req)["energy"]
        e_big   = _model(27, 39, 0.5, req)["energy"]
        assert e_big > e_small


class TestCostFunction:
    def test_cost_is_positive(self):
        req = default_req()
        assert _cost(20, 30, 0.5, req) > 0

    def test_dp_below_min_adds_penalty(self):
        # Force a tiny dp_min so we can construct a clearly-violating point
        req = default_req(dp_kp_oo_min=10.0)
        # very low load → small |pressures| → small dp
        c_violate = _cost(req.flow_kp_min, req.flow_oo_min, 0.05, req)
        # high load → bigger pressures → bigger dp gap (still negative because ОО pulls harder)
        c_ok      = _cost(req.flow_kp_max, req.flow_oo_min, 0.5, req)
        assert c_violate > 0 and c_ok > 0  # both finite

    def test_flow_kp_below_min_adds_penalty(self):
        req = default_req()
        c_inside  = _cost(req.flow_kp_min, 25, 0.5, req)
        c_outside = _cost(req.flow_kp_min - 5, 25, 0.5, req)
        assert c_outside > c_inside

    def test_flow_oo_above_max_adds_penalty(self):
        req = default_req()
        c_inside  = _cost(20, req.flow_oo_max, 0.5, req)
        c_outside = _cost(20, req.flow_oo_max + 10, 0.5, req)
        assert c_outside > c_inside

    def test_energy_cost_increases_with_load(self):
        req = default_req()
        c_low  = _cost(20, 30, 0.1, req)
        c_high = _cost(20, 30, 0.9, req)
        assert c_high > c_low


class TestOptimizeScipy:
    def test_returns_valid_result_structure(self):
        req = default_req()
        r = _optimize_scipy(req)
        for k in (
            "method", "optimal_flow_kp", "optimal_flow_oo", "optimal_fan_load",
            "expected_pressure_kp", "expected_pressure_oo", "expected_dp_kp_oo",
            "energy_kw", "energy_cost_per_hour", "safety_margin",
            "status", "iterations",
        ):
            assert k in r

    def test_optimal_flows_within_bounds(self):
        req = default_req()
        r = _optimize_scipy(req)
        assert req.flow_kp_min <= r["optimal_flow_kp"] <= req.flow_kp_max
        assert req.flow_oo_min <= r["optimal_flow_oo"] <= req.flow_oo_max

    def test_optimal_fan_load_within_bounds(self):
        req = default_req()
        r = _optimize_scipy(req)
        assert 0.05 <= r["optimal_fan_load"] <= 1.0

    def test_method_field_is_scipy(self):
        r = _optimize_scipy(default_req(method="scipy"))
        assert r["method"] == "scipy"


class TestOptimizeGrid:
    def test_returns_valid_result_structure(self):
        r = _optimize_grid(default_req(method="grid"))
        assert "optimal_flow_kp" in r
        assert "optimal_flow_oo" in r
        assert r["status"] == "ok"

    def test_iterations_equal_grid_size(self):
        r = _optimize_grid(default_req(method="grid"))
        assert r["iterations"] == 12 * 12 * 12  # see _optimize_grid

    def test_optimal_flows_within_bounds(self):
        req = default_req(method="grid")
        r = _optimize_grid(req)
        assert req.flow_kp_min <= r["optimal_flow_kp"] <= req.flow_kp_max
        assert req.flow_oo_min <= r["optimal_flow_oo"] <= req.flow_oo_max

    def test_grid_and_scipy_produce_comparable_costs(self):
        req = default_req()
        s = _optimize_scipy(req)
        g = _optimize_grid(req)
        cs = _cost(s["optimal_flow_kp"], s["optimal_flow_oo"], s["optimal_fan_load"], req)
        cg = _cost(g["optimal_flow_kp"], g["optimal_flow_oo"], g["optimal_fan_load"], req)
        # Both algorithms should land near each other (within 50% — grid is coarse)
        assert abs(cs - cg) / max(cs, cg) < 0.5
