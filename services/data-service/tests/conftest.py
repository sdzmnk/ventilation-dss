"""
Shared fixtures for data-service tests.

Strategy:
- Patch asyncpg.create_pool so the startup event does not open a real DB connection.
- Patch _seed_history and asyncio.create_task to prevent background workers from running.
- Override auth_required dependency so every test has a valid authenticated user by default.
- Provide a `conn` fixture for setting up per-test DB return values.
"""

import asyncio
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
ENGINEER_HEADERS = {"Authorization": f"Bearer {make_token('engineer')}"}


@pytest.fixture(scope="session")
def mock_conn():
    """A single AsyncMock connection reused across the session."""
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
def patch_db_and_startup(mock_pool, mock_conn):
    """Prevent real DB connections and background tasks for all tests."""
    async def fake_create_pool(**kwargs):
        return mock_pool

    async def fake_seed():
        pass

    with patch("asyncpg.create_pool", side_effect=fake_create_pool), \
         patch("app.main._seed_history", fake_seed), \
         patch("asyncio.create_task"):
        import app.main as m
        m.pool = mock_pool
        yield mock_conn


@pytest.fixture(scope="session")
def client(patch_db_and_startup):
    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
