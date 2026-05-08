"""Tests for /analytic/optimize and /analytic/runs against the new payload."""

import pytest
from tests.conftest import HEADERS


VALID_OPTIMIZE_PAYLOAD = {
    "method": "scipy",
    "fan_power_kw": 15.0,
    "energy_cost_kwh": 0.12,
    "pressure_kp_target": -10.0,
    "pressure_oo_target": -17.0,
    "dp_kp_oo_min": 2.0,
    "flow_kp_min": 10.0,
    "flow_kp_max": 28.0,
    "flow_oo_min": 15.0,
    "flow_oo_max": 40.0,
    "filter_efficiency": 0.999,
    "current_wind_speed": 2.0,
}


class TestOptimizeEndpoint:
    def test_optimize_requires_auth(self, client):
        resp = client.post("/analytic/optimize", json=VALID_OPTIMIZE_PAYLOAD)
        assert resp.status_code == 401

    def test_optimize_scipy_success(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {"id": 1}
        resp = client.post("/analytic/optimize", json=VALID_OPTIMIZE_PAYLOAD, headers=HEADERS)
        assert resp.status_code == 200

    def test_optimize_scipy_response_has_all_fields(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {"id": 1}
        resp = client.post("/analytic/optimize", json=VALID_OPTIMIZE_PAYLOAD, headers=HEADERS)
        data = resp.json()
        for k in (
            "method", "optimal_flow_kp", "optimal_flow_oo", "optimal_fan_load",
            "expected_pressure_kp", "expected_pressure_oo", "expected_dp_kp_oo",
            "energy_kw", "energy_cost_per_hour", "safety_margin",
            "status", "iterations", "id",
        ):
            assert k in data

    def test_optimize_flows_within_bounds(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {"id": 2}
        resp = client.post("/analytic/optimize", json=VALID_OPTIMIZE_PAYLOAD, headers=HEADERS)
        data = resp.json()
        assert 10.0 <= data["optimal_flow_kp"] <= 28.0
        assert 15.0 <= data["optimal_flow_oo"] <= 40.0

    def test_optimize_fan_load_within_bounds(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {"id": 3}
        resp = client.post("/analytic/optimize", json=VALID_OPTIMIZE_PAYLOAD, headers=HEADERS)
        data = resp.json()
        assert 0.0 < data["optimal_fan_load"] <= 1.0

    def test_optimize_grid_method(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {"id": 4}
        payload = {**VALID_OPTIMIZE_PAYLOAD, "method": "grid"}
        resp = client.post("/analytic/optimize", json=payload, headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] == "grid"
        assert data["iterations"] == 12 * 12 * 12

    def test_optimize_invalid_flow_kp_range_returns400(self, client):
        payload = {**VALID_OPTIMIZE_PAYLOAD, "flow_kp_min": 28.0, "flow_kp_max": 10.0}
        resp = client.post("/analytic/optimize", json=payload, headers=HEADERS)
        assert resp.status_code == 400

    def test_optimize_zero_fan_power_returns422(self, client):
        payload = {**VALID_OPTIMIZE_PAYLOAD, "fan_power_kw": 0}
        resp = client.post("/analytic/optimize", json=payload, headers=HEADERS)
        assert resp.status_code == 422

    def test_optimize_filter_efficiency_above_1_returns422(self, client):
        payload = {**VALID_OPTIMIZE_PAYLOAD, "filter_efficiency": 1.5}
        resp = client.post("/analytic/optimize", json=payload, headers=HEADERS)
        assert resp.status_code == 422

    def test_optimize_saves_run_to_db(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {"id": 10}
        client.post("/analytic/optimize", json=VALID_OPTIMIZE_PAYLOAD, headers=HEADERS)
        mock_conn.fetchrow.assert_called()


class TestRunsEndpoint:
    def test_runs_requires_auth(self, client):
        resp = client.get("/analytic/runs")
        assert resp.status_code == 401

    def test_runs_returns_list(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/analytic/runs", headers=HEADERS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_runs_returns_correct_fields(self, client, mock_conn):
        from datetime import datetime, timezone
        mock_conn.fetch.return_value = [{
            "id": 1,
            "method": "scipy",
            "inputs": '{"method":"scipy","fan_power_kw":15.0}',
            "result": '{"optimal_flow_kp":18.0}',
            "status": "ok",
            "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "finished_at": datetime(2024, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        }]
        resp = client.get("/analytic/runs", headers=HEADERS)
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["method"] == "scipy"
        assert "inputs" in data[0]
        assert "result" in data[0]

    def test_runs_limit_default_50(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        client.get("/analytic/runs", headers=HEADERS)
        call_args = mock_conn.fetch.call_args
        assert call_args is not None
        assert 50 in call_args.args or 50 in (call_args.kwargs or {}).values()
