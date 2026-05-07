"""Tests for /simulate endpoint."""

import pytest
from tests.conftest import HEADERS, ADMIN_HEADERS, ENGINEER_HEADERS


class TestSimulate:
    def test_simulate_requires_auth(self, client):
        resp = client.post("/simulate")
        assert resp.status_code == 401

    def test_simulate_operator_forbidden(self, client):
        resp = client.post("/simulate", headers=HEADERS)
        assert resp.status_code == 403

    def test_simulate_admin_success(self, client, mock_conn):
        sensor_rows = [
            {"id": 1, "sensor_type": "radiation"},
            {"id": 2, "sensor_type": "pressure"},
        ]
        mock_conn.fetch.return_value = sensor_rows
        mock_conn.execute.return_value = None

        resp = client.post("/simulate?points_per_sensor=5", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert "inserted" in data
        assert data["inserted"] == 10  # 2 sensors * 5 points
        assert data["sensors"] == 2

    def test_simulate_engineer_success(self, client, mock_conn):
        mock_conn.fetch.return_value = [{"id": 1, "sensor_type": "airflow"}]
        mock_conn.execute.return_value = None

        resp = client.post("/simulate?points_per_sensor=3", headers=ENGINEER_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["inserted"] == 3

    def test_simulate_points_validation_min(self, client):
        resp = client.post("/simulate?points_per_sensor=0", headers=ADMIN_HEADERS)
        assert resp.status_code == 422

    def test_simulate_points_validation_max(self, client):
        resp = client.post("/simulate?points_per_sensor=9999", headers=ADMIN_HEADERS)
        assert resp.status_code == 422

    def test_simulate_default_points_is20(self, client, mock_conn):
        mock_conn.fetch.return_value = [{"id": 1, "sensor_type": "temperature"}]
        mock_conn.execute.return_value = None

        resp = client.post("/simulate", headers=ADMIN_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["inserted"] == 20
