"""Tests for /analytic/stats and /analytic/trend endpoints."""

import pytest
from datetime import datetime, timezone
from tests.conftest import HEADERS


class TestStatsEndpoint:
    def test_stats_requires_auth(self, client):
        resp = client.get("/analytic/stats")
        assert resp.status_code == 401

    def test_stats_returns_list(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/analytic/stats", headers=HEADERS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_stats_returns_correct_fields(self, client, mock_conn):
        mock_conn.fetch.return_value = [{
            "sensor_type": "radiation",
            "count": 100,
            "mean": 8.5,
            "min": 5.0,
            "max": 12.0,
            "p95": 11.5,
        }]
        resp = client.get("/analytic/stats", headers=HEADERS)
        data = resp.json()
        assert len(data) == 1
        s = data[0]
        assert s["sensor_type"] == "radiation"
        assert s["count"] == 100
        assert s["mean"] == 8.5
        assert s["min"] == 5.0
        assert s["max"] == 12.0
        assert s["p95"] == 11.5

    def test_stats_empty_db_returns_empty(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/analytic/stats", headers=HEADERS)
        assert resp.json() == []

    def test_stats_multiple_sensor_types(self, client, mock_conn):
        mock_conn.fetch.return_value = [
            {"sensor_type": "airflow", "count": 50, "mean": 18000.0, "min": 15000.0, "max": 21000.0, "p95": 20500.0},
            {"sensor_type": "radiation", "count": 50, "mean": 8.0, "min": 5.5, "max": 11.0, "p95": 10.5},
        ]
        resp = client.get("/analytic/stats", headers=HEADERS)
        assert len(resp.json()) == 2

    def test_stats_hours_param(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/analytic/stats?hours=48", headers=HEADERS)
        assert resp.status_code == 200


class TestTrendEndpoint:
    def test_trend_requires_auth(self, client):
        resp = client.get("/analytic/trend?sensor_type=radiation")
        assert resp.status_code == 401

    def test_trend_returns_list(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/analytic/trend?sensor_type=radiation", headers=HEADERS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_trend_returns_correct_fields(self, client, mock_conn):
        mock_conn.fetch.return_value = [{
            "bucket": datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            "value": 9.5,
        }]
        resp = client.get("/analytic/trend?sensor_type=radiation", headers=HEADERS)
        data = resp.json()
        assert len(data) == 1
        assert "t" in data[0]
        assert data[0]["value"] == 9.5

    def test_trend_multiple_buckets(self, client, mock_conn):
        mock_conn.fetch.return_value = [
            {"bucket": datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc), "value": 8.0},
            {"bucket": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), "value": 9.0},
            {"bucket": datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), "value": 7.5},
        ]
        resp = client.get("/analytic/trend?sensor_type=airflow", headers=HEADERS)
        assert len(resp.json()) == 3

    def test_trend_with_hours_param(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/analytic/trend?sensor_type=pressure&hours=72", headers=HEADERS)
        assert resp.status_code == 200

    def test_trend_with_bucket_minutes_param(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/analytic/trend?sensor_type=temperature&bucket_minutes=30", headers=HEADERS)
        assert resp.status_code == 200

    def test_trend_empty_returns_empty_list(self, client, mock_conn):
        mock_conn.fetch.return_value = []
        resp = client.get("/analytic/trend?sensor_type=radiation", headers=HEADERS)
        assert resp.json() == []
