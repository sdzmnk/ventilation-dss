"""Tests for /readings endpoints."""

import pytest
from datetime import datetime, timezone
from tests.conftest import HEADERS, ADMIN_HEADERS


READING_ROW = {
    "id": 1,
    "sensor_id": 1,
    "value": 8.5,
    "measured_at": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
}

LATEST_ROW = {
    "sensor_id": 1,
    "sensor_code": "S-RAD-01",
    "sensor_type": "radiation",
    "unit": "мкЗв/год",
    "zone_id": 1,
    "zone_code": "Z-01",
    "zone_name": "Зона 1",
    "value": 9.2,
    "measured_at": datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
}


class TestListReadings:
    def test_list_readings_requires_auth(self, client):
        resp = client.get("/readings")
        assert resp.status_code == 401

    def test_list_readings_returns200(self, client, mock_conn):
        mock_conn.fetch.return_value = [READING_ROW]
        resp = client.get("/readings", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_readings_correct_fields(self, client, mock_conn):
        mock_conn.fetch.return_value = [READING_ROW]
        resp = client.get("/readings", headers=HEADERS)
        r = resp.json()[0]
        assert r["sensor_id"] == 1
        assert r["value"] == 8.5
        assert "measured_at" in r

    def test_list_readings_empty(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/readings", headers=HEADERS)
        assert resp.json() == []

    def test_list_readings_hours_param_validated(self, client):
        resp = client.get("/readings?hours=0", headers=HEADERS)
        assert resp.status_code == 422

    def test_list_readings_hours_max_validated(self, client):
        resp = client.get("/readings?hours=9999", headers=HEADERS)
        assert resp.status_code == 422

    def test_list_readings_limit_validated(self, client):
        resp = client.get("/readings?limit=0", headers=HEADERS)
        assert resp.status_code == 422


class TestCreateReading:
    def test_create_reading_requires_auth(self, client):
        resp = client.post("/readings", json={"sensor_id": 1, "value": 8.0})
        assert resp.status_code == 401

    def test_create_reading_success(self, client, mock_conn):
        mock_conn.fetchrow.return_value = READING_ROW
        resp = client.post("/readings",
                           json={"sensor_id": 1, "value": 8.5},
                           headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["sensor_id"] == 1
        assert resp.json()["value"] == 8.5

    def test_create_reading_with_timestamp(self, client, mock_conn):
        mock_conn.fetchrow.return_value = READING_ROW
        resp = client.post("/readings",
                           json={"sensor_id": 1, "value": 9.0, "measured_at": "2024-01-01T10:00:00Z"},
                           headers=HEADERS)
        assert resp.status_code == 200


class TestLatestReadings:
    def test_latest_requires_auth(self, client):
        resp = client.get("/readings/latest")
        assert resp.status_code == 401

    def test_latest_returns200(self, client, mock_conn):
        mock_conn.fetch.return_value = [LATEST_ROW]
        resp = client.get("/readings/latest", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_latest_correct_fields(self, client, mock_conn):
        mock_conn.fetch.return_value = [LATEST_ROW]
        resp = client.get("/readings/latest", headers=HEADERS)
        r = resp.json()[0]
        assert r["sensor_id"] == 1
        assert r["sensor_type"] == "radiation"
        assert r["value"] == 9.2
        assert r["zone_name"] == "Зона 1"

    def test_latest_empty_whenNoSensors(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/readings/latest", headers=HEADERS)
        assert resp.json() == []
