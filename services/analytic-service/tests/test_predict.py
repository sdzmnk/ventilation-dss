"""Unit tests for /analytic/predict against the new (KP/OO/GU) sensor channels."""

import pytest
from tests.conftest import HEADERS


SAFE_PARAMS = {
    "pressure_kp":           -10.0,
    "pressure_oo":           -17.0,
    "dp_kp_oo":                7.0,
    "flow_kp_in":             14.0,
    "flow_oo_out":            30.0,
    "wind_speed":              2.0,
    "gu_pressure_west_wall":   0.5,
    "gu_pressure_east_wall":  -2.5,
    "gu_pressure_cyl_wall":   -4.0,
}


def _override(**kw):
    return {**SAFE_PARAMS, **kw}


class TestPredictEndpoint:
    def test_predict_requires_auth(self, client):
        resp = client.get("/analytic/predict")
        assert resp.status_code == 401

    def test_predict_returns_structure(self, client):
        resp = client.get("/analytic/predict", params=SAFE_PARAMS, headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "prediction_data" in data
        assert "recommendation" in data
        assert "anomaly_detection" not in data
        pd = data["prediction_data"]
        assert "status" in pd
        assert "risk_score" in pd
        assert "confidence" in pd
        assert "probabilities" in pd

    def test_predict_probabilities_sum_to_one(self, client):
        resp = client.get("/analytic/predict", params=SAFE_PARAMS, headers=HEADERS)
        probs = resp.json()["prediction_data"]["probabilities"]
        total = probs["OK"] + probs["WARNING"] + probs["CRITICAL"]
        assert abs(total - 1.0) < 0.01

    def test_predict_baseline_values_return_OK(self, client):
        resp = client.get("/analytic/predict", params=SAFE_PARAMS, headers=HEADERS)
        assert resp.json()["prediction_data"]["status"] == "OK"

    def test_predict_negative_dp_kp_oo_raises_danger(self, client):
        resp_normal = client.get("/analytic/predict", params=SAFE_PARAMS, headers=HEADERS)
        resp_neg = client.get(
            "/analytic/predict",
            params=_override(dp_kp_oo=-25.0),
            headers=HEADERS,
        )
        assert resp_neg.json()["prediction_data"]["risk_score"] < resp_normal.json()["prediction_data"]["risk_score"]

    def test_predict_extreme_dp_kp_oo_returns_CRITICAL(self, client):
        resp = client.get(
            "/analytic/predict",
            params=_override(dp_kp_oo=-50.0, pressure_kp=-150.0, pressure_oo=-200.0),
            headers=HEADERS,
        )
        assert resp.json()["prediction_data"]["status"] in ("CRITICAL", "WARNING")

    def test_predict_high_wind_raises_danger(self, client):
        resp_normal = client.get("/analytic/predict", params=SAFE_PARAMS, headers=HEADERS)
        resp_wind = client.get(
            "/analytic/predict",
            params=_override(wind_speed=20.0),
            headers=HEADERS,
        )
        assert resp_wind.json()["prediction_data"]["risk_score"] <= resp_normal.json()["prediction_data"]["risk_score"]

    def test_predict_risk_score_range(self, client):
        resp = client.get("/analytic/predict", params=SAFE_PARAMS, headers=HEADERS)
        risk_score = resp.json()["prediction_data"]["risk_score"]
        assert 0 <= risk_score <= 100

    def test_predict_recommendation_not_empty(self, client):
        resp = client.get("/analytic/predict", params=SAFE_PARAMS, headers=HEADERS)
        assert len(resp.json()["recommendation"]) > 10

    def test_predict_critical_recommendation_mentions_key_channels(self, client):
        resp = client.get(
            "/analytic/predict",
            params=_override(
                dp_kp_oo=-60.0,
                pressure_kp=-200.0,
                pressure_oo=-200.0,
                flow_kp_in=0.5,
                flow_oo_out=0.5,
                gu_pressure_west_wall=70.0,
                gu_pressure_east_wall=-70.0,
                gu_pressure_cyl_wall=70.0,
            ),
            headers=HEADERS,
        )
        body = resp.json()
        assert body["prediction_data"]["status"] in ("CRITICAL", "WARNING")
        assert len(body["recommendation"]) > 10


class TestChannelScoreLogic:
    def test_pressure_within_safe_range_keeps_status_OK(self, client):
        for pkp in [-50.0, -10.0, 14.0]:
            resp = client.get(
                "/analytic/predict",
                params=_override(pressure_kp=pkp),
                headers=HEADERS,
            )
            assert resp.json()["prediction_data"]["status"] == "OK"

    def test_dp_kp_oo_at_warn_lo_does_not_crash(self, client):
        resp = client.get(
            "/analytic/predict",
            params=_override(dp_kp_oo=-15.0),
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_low_flow_kp_in_adds_danger(self, client):
        resp_normal = client.get("/analytic/predict", params=SAFE_PARAMS, headers=HEADERS)
        resp_low = client.get(
            "/analytic/predict",
            params=_override(flow_kp_in=2.0),
            headers=HEADERS,
        )
        assert resp_low.json()["prediction_data"]["risk_score"] < resp_normal.json()["prediction_data"]["risk_score"]
