"""Tests for the health endpoint and helper functions."""

import pytest
from app.main import _baseline


class TestBaseline:
    def test_radiation_baseline(self):
        b = _baseline("radiation")
        assert b["mean"] == 8.0
        assert b["noise"] == 2.5

    def test_pressure_baseline(self):
        b = _baseline("pressure")
        assert b["mean"] == -120.0
        assert b["noise"] == 25.0

    def test_airflow_baseline(self):
        b = _baseline("airflow")
        assert b["mean"] == 18000.0
        assert b["noise"] == 2500.0

    def test_temperature_baseline(self):
        b = _baseline("temperature")
        assert b["mean"] == 22.0
        assert b["noise"] == 1.5

    def test_unknown_type_returnsDefault(self):
        b = _baseline("unknown_sensor")
        assert b["mean"] == 1.0
        assert b["noise"] == 0.1


class TestHealthEndpoint:
    def test_health_returns200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_hasStatusOk(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "data-service"
