"""
Unit tests for the classification/prediction logic.
Uses direct query params so no DB is needed (all values passed explicitly).
"""

import pytest
from tests.conftest import HEADERS


class TestPredictEndpoint:
    def test_predict_requires_auth(self, client):
        resp = client.get("/analytic/predict")
        assert resp.status_code == 401

    def test_predict_returns_structure(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 8.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "prediction_data" in data
        assert "recommendation" in data
        pd = data["prediction_data"]
        assert "status" in pd
        assert "risk_score" in pd
        assert "confidence" in pd
        assert "probabilities" in pd

    def test_predict_probabilities_sum_to_one(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 8.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        probs = resp.json()["prediction_data"]["probabilities"]
        total = probs["OK"] + probs["WARNING"] + probs["CRITICAL"]
        assert abs(total - 1.0) < 0.01

    def test_predict_baseline_values_return_OK(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 8.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        assert resp.json()["prediction_data"]["status"] == "OK"

    def test_predict_high_radiation_returns_WARNING_or_CRITICAL(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 19.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        status = resp.json()["prediction_data"]["status"]
        assert status in ("WARNING", "CRITICAL")

    def test_predict_critical_radiation_returns_CRITICAL(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 25.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        assert resp.json()["prediction_data"]["status"] == "CRITICAL"

    def test_predict_low_airflow_raises_danger(self, client):
        resp_normal = client.get(
            "/analytic/predict",
            params={"radiation": 8.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        resp_low = client.get(
            "/analytic/predict",
            params={"radiation": 8.0, "pressure": -120.0, "airflow": 100.0, "temperature": 22.0},
            headers=HEADERS,
        )
        score_normal = resp_normal.json()["prediction_data"]["risk_score"]
        score_low = resp_low.json()["prediction_data"]["risk_score"]
        assert score_low < score_normal  # risk_score is (1 - composite)*100; lower means more danger

    def test_predict_risk_score_range(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 8.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        risk_score = resp.json()["prediction_data"]["risk_score"]
        assert 0 <= risk_score <= 100

    def test_predict_recommendation_not_empty(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 8.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        assert len(resp.json()["recommendation"]) > 10

    def test_predict_critical_recommendation_contains_emergency_text(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 30.0, "pressure": -300.0, "airflow": 100.0, "temperature": 40.0},
            headers=HEADERS,
        )
        rec = resp.json()["recommendation"]
        assert "КРИТИЧНА" in rec or "критична" in rec.lower() or "аварійн" in rec.lower()


class TestDangerScoreLogic:
    """Tests that verify the danger score classification boundaries directly via predict endpoint."""

    def test_radiation_below_16_is_safe(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 15.9, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        assert resp.json()["prediction_data"]["status"] == "OK"

    def test_radiation_exactly_20_is_warning_or_critical(self, client):
        resp = client.get(
            "/analytic/predict",
            params={"radiation": 20.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 22.0},
            headers=HEADERS,
        )
        assert resp.json()["prediction_data"]["status"] in ("WARNING", "CRITICAL")

    def test_pressure_within_safe_range_has_zero_pres_score(self, client):
        for pressure in [-180.0, -120.0, -60.0]:
            resp = client.get(
                "/analytic/predict",
                params={"radiation": 8.0, "pressure": pressure, "airflow": 18000.0, "temperature": 22.0},
                headers=HEADERS,
            )
            assert resp.json()["prediction_data"]["status"] == "OK"

    def test_temperature_above_28_adds_danger(self, client):
        resp_normal = client.get(
            "/analytic/predict",
            params={"radiation": 8.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 27.0},
            headers=HEADERS,
        )
        resp_hot = client.get(
            "/analytic/predict",
            params={"radiation": 8.0, "pressure": -120.0, "airflow": 18000.0, "temperature": 35.0},
            headers=HEADERS,
        )
        score_normal = resp_normal.json()["prediction_data"]["risk_score"]
        score_hot = resp_hot.json()["prediction_data"]["risk_score"]
        assert score_hot < score_normal
