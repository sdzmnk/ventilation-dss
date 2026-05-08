"""Shared fixtures for analytic-service tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

JWT_SECRET = "dev-secret"
JWT_ALG = "HS256"


def make_token(role: str = "operator", user_id: int = 1) -> str:
    import jwt
    payload = {"sub": str(user_id), "role": role, "username": "testuser", "kind": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


HEADERS = {"Authorization": f"Bearer {make_token('operator')}"}
ADMIN_HEADERS = {"Authorization": f"Bearer {make_token('admin')}"}


@pytest.fixture(scope="session")
def mock_conn():
    conn = AsyncMock()
    conn.fetch.return_value = []
    conn.fetchrow.return_value = None
    conn.fetchval.return_value = 0
    conn.execute.return_value = None
    return conn


@pytest.fixture(scope="session")
def mock_pool(mock_conn):
    pool = MagicMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    pool.acquire.return_value = cm
    pool.close = AsyncMock()
    return pool


@pytest.fixture(scope="session", autouse=True)
def patch_db(mock_pool, mock_conn):
    async def fake_create_pool(**kwargs):
        return mock_pool

    with patch("asyncpg.create_pool", side_effect=fake_create_pool):
        import app.main as m
        m.pool = mock_pool

        # Populate baselines + thresholds so /analytic/predict works in
        # tests without the mounted ventilation_baselines.json file.
        m._BASELINES = {
            "pressure_kp":           {"p05": -22, "p50": -10.5, "p95":   8,  "std": 13.7, "min": -150, "max":  16},
            "pressure_oo":           {"p05": -29, "p50": -17.0, "p95":   4,  "std": 13.1, "min":  -77, "max":  40},
            "flow_kp_in":            {"p05":  11, "p50":  14.0, "p95":  21,  "std":  3.0, "min":    0, "max":  28},
            "flow_oo_out":           {"p05":  18, "p50":  30.0, "p95":  37,  "std":  7.8, "min":    0, "max":  41},
            "flow_oo_in":            {"p05":   0, "p50":   0.0, "p95":   0,  "std":  0.7, "min":    0, "max":  14},
            "dp_kp_os":              {"p05": -22, "p50": -10.5, "p95":   8,  "std": 13.7, "min": -150, "max":  16},
            "dp_oo_os_8":            {"p05": -29, "p50": -17.0, "p95":   4,  "std": 13.1, "min":  -77, "max":  40},
            "dp_oo_os_9":            {"p05": -32, "p50": -19.0, "p95":   3,  "std": 13.4, "min":  -97, "max":  23},
            "dp_kp_oo_by":           {"p05":   1, "p50":   7.0, "p95":  14,  "std":  4.0, "min":  -50, "max":  26},
            "dp_kp_oo_bz":           {"p05":   1, "p50":   5.7, "p95":  13,  "std":  4.3, "min":   -1, "max":  28},
            "dp_kp_oo_ca":           {"p05":   2, "p50":   6.5, "p95":  12,  "std":  3.2, "min":  -21, "max":  22},
            "wind_speed":            {"p05":   0.5,"p50":   2.0,"p95":   4.5,"std":  1.2, "min":    0, "max":   9.7},
            "gu_pressure_west_wall": {"p05": -10, "p50":   0.6, "p95":  10,  "std":  7.4, "min":  -54, "max":  60},
            "gu_pressure_east_wall": {"p05": -10, "p50":  -2.5, "p95":   8,  "std":  5.8, "min":  -78, "max":  25},
            "gu_pressure_cyl_wall":  {"p05": -12, "p50":  -4.0, "p95":   0,  "std":  5.0, "min":  -61, "max":   0},
            "gu_pressure_west_gap":  {"p05": -10, "p50":   0.6, "p95":  10,  "std":  6.8, "min":  -46, "max":  55},
            "gu_pressure_east_gap":  {"p05": -10, "p50":  -2.2, "p95":   8,  "std":  5.4, "min":  -54, "max":  26},
            "gu_pressure_vsro":      {"p05": -10, "p50":  -2.6, "p95":   8,  "std":  6.3, "min":  -45, "max":  42},
            "gu_sigma_008":          {"p05":  -8, "p50":  -0.7, "p95":   8,  "std":  6.4, "min":  -82, "max":  61},
            "gu_sigma_009":          {"p05":  -8, "p50":  -0.1, "p95":   8,  "std":  5.7, "min":  -30, "max":  39},
            "gu_sigma_kp_os":        {"p05":  -8, "p50":   1.2, "p95":  12,  "std":  8.1, "min":  -33, "max":  62},
        }
        m.THRESHOLDS = m._derive_thresholds()
        yield mock_conn


@pytest.fixture(scope="session")
def client(patch_db):
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
