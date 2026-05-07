"""Tests for /sensors endpoints."""

import pytest
from tests.conftest import HEADERS, ADMIN_HEADERS, ENGINEER_HEADERS


SENSOR_ROW = {
    "id": 1,
    "zone_id": 1,
    "code": "S-RAD-01",
    "sensor_type": "radiation",
    "unit": "мкЗв/год",
}


class TestListSensors:
    def test_list_sensors_requires_auth(self, client):
        resp = client.get("/sensors")
        assert resp.status_code == 401

    def test_list_sensors_returns200(self, client, mock_conn):
        mock_conn.fetch.return_value = [SENSOR_ROW]
        resp = client.get("/sensors", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_list_sensors_correct_fields(self, client, mock_conn):
        mock_conn.fetch.return_value = [SENSOR_ROW]
        resp = client.get("/sensors", headers=HEADERS)
        s = resp.json()[0]
        assert s["code"] == "S-RAD-01"
        assert s["sensor_type"] == "radiation"
        assert s["unit"] == "мкЗв/год"

    def test_list_sensors_empty(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/sensors", headers=HEADERS)
        assert resp.json() == []


class TestCreateSensor:
    def test_create_sensor_requires_engineer_role(self, client, mock_conn):
        resp = client.post("/sensors",
                           json={"code": "S-NEW", "sensor_type": "temperature", "unit": "°C"},
                           headers=HEADERS)
        assert resp.status_code == 403

    def test_create_sensor_admin_success(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {
            "id": 10, "zone_id": None, "code": "S-NEW", "sensor_type": "temperature", "unit": "°C"
        }
        resp = client.post("/sensors",
                           json={"code": "S-NEW", "sensor_type": "temperature", "unit": "°C"},
                           headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["code"] == "S-NEW"

    def test_create_sensor_engineer_success(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {
            "id": 11, "zone_id": 1, "code": "S-PRE", "sensor_type": "pressure", "unit": "Па"
        }
        resp = client.post("/sensors",
                           json={"zone_id": 1, "code": "S-PRE", "sensor_type": "pressure", "unit": "Па"},
                           headers=ENGINEER_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["sensor_type"] == "pressure"


class TestUpdateSensor:
    def test_update_sensor_notFound_returns404(self, client, mock_conn):
        mock_conn.fetchrow.return_value = None
        resp = client.put("/sensors/999",
                          json={"code": "S-X", "sensor_type": "airflow", "unit": "м³/год"},
                          headers=ADMIN_HEADERS)
        assert resp.status_code == 404

    def test_update_sensor_success(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {
            "id": 1, "zone_id": 2, "code": "S-RAD-01-UPD", "sensor_type": "radiation", "unit": "мкЗв/год"
        }
        resp = client.put("/sensors/1",
                          json={"zone_id": 2, "code": "S-RAD-01-UPD", "sensor_type": "radiation", "unit": "мкЗв/год"},
                          headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["code"] == "S-RAD-01-UPD"


class TestDeleteSensor:
    def test_delete_sensor_admin_success(self, client, mock_conn):
        mock_conn.execute.return_value = None
        resp = client.delete("/sensors/1", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 1

    def test_delete_sensor_engineer_forbidden(self, client):
        resp = client.delete("/sensors/1", headers=ENGINEER_HEADERS)
        assert resp.status_code == 403
