"""Tests for /zones endpoints."""

import pytest
from tests.conftest import HEADERS, ADMIN_HEADERS, ENGINEER_HEADERS


ZONE_ROW = {"id": 1, "code": "Z-01", "name": "Зона 1", "description": "Основна зона"}


class TestListZones:
    def test_list_zones_requires_auth(self, client):
        resp = client.get("/zones")
        assert resp.status_code == 401

    def test_list_zones_operator_returns200(self, client, mock_conn):
        mock_conn.fetch.return_value = [ZONE_ROW]
        resp = client.get("/zones", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_zones_returns_correct_fields(self, client, mock_conn):
        mock_conn.fetch.return_value = [ZONE_ROW]
        resp = client.get("/zones", headers=HEADERS)
        zone = resp.json()[0]
        assert zone["id"] == 1
        assert zone["code"] == "Z-01"
        assert zone["name"] == "Зона 1"

    def test_list_zones_empty(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/zones", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateZone:
    def test_create_zone_requires_auth(self, client):
        resp = client.post("/zones", json={"code": "Z-99", "name": "Test"})
        assert resp.status_code == 401

    def test_create_zone_operator_forbidden(self, client, mock_conn):
        resp = client.post("/zones",
                           json={"code": "Z-99", "name": "Test"},
                           headers=HEADERS)
        assert resp.status_code == 403

    def test_create_zone_admin_success(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {
            "id": 5, "code": "Z-99", "name": "New Zone", "description": None
        }
        resp = client.post("/zones",
                           json={"code": "Z-99", "name": "New Zone"},
                           headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["code"] == "Z-99"

    def test_create_zone_engineer_success(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {
            "id": 6, "code": "Z-ENG", "name": "Eng Zone", "description": "By engineer"
        }
        resp = client.post("/zones",
                           json={"code": "Z-ENG", "name": "Eng Zone", "description": "By engineer"},
                           headers=ENGINEER_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["code"] == "Z-ENG"


class TestUpdateZone:
    def test_update_zone_notFound_returns404(self, client, mock_conn):
        mock_conn.fetchrow.return_value = None
        resp = client.put("/zones/999",
                          json={"code": "Z-X", "name": "X"},
                          headers=ADMIN_HEADERS)
        assert resp.status_code == 404

    def test_update_zone_success(self, client, mock_conn):
        mock_conn.fetchrow.return_value = {
            "id": 1, "code": "Z-01-UPD", "name": "Updated", "description": None
        }
        resp = client.put("/zones/1",
                          json={"code": "Z-01-UPD", "name": "Updated"},
                          headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["code"] == "Z-01-UPD"


class TestDeleteZone:
    def test_delete_zone_admin_success(self, client, mock_conn):
        mock_conn.execute.return_value = None
        resp = client.delete("/zones/1", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 1

    def test_delete_zone_operator_forbidden(self, client):
        resp = client.delete("/zones/1", headers=HEADERS)
        assert resp.status_code == 403
