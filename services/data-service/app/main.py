import asyncio
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncpg
import jwt
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

app = FastAPI(title="Data Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            database=os.getenv("POSTGRES_DB"),
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            min_size=1,
            max_size=5,
            ssl=False,
        )
    return pool


def auth_required(token: Optional[str] = Depends(oauth2)) -> dict:
    if not token:
        raise HTTPException(401, "Потрібна автентифікація")
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(401, "Недійсний токен")


def role_required(*roles: str):
    def _dep(claims: dict = Depends(auth_required)) -> dict:
        if claims.get("role") not in roles:
            raise HTTPException(403, "Недостатньо прав")
        return claims
    return _dep


# ===== Models =====
class ZoneIn(BaseModel):
    code: str
    name: str
    description: Optional[str] = None


class ZoneOut(ZoneIn):
    id: int


class SensorIn(BaseModel):
    zone_id: Optional[int] = None
    code: str
    sensor_type: str
    unit: str


class SensorOut(SensorIn):
    id: int


class ReadingIn(BaseModel):
    sensor_id: int
    value: float
    measured_at: Optional[datetime] = None


class ReadingOut(BaseModel):
    id: int
    sensor_id: int
    value: float
    measured_at: datetime


# ===== Lifecycle =====
_ingest_task: Optional[asyncio.Task] = None


@app.on_event("startup")
async def _startup() -> None:
    await get_pool()
    await _seed_history()
    global _ingest_task
    _ingest_task = asyncio.create_task(_ingest_loop())


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _ingest_task:
        _ingest_task.cancel()
    if pool:
        await pool.close()


async def _seed_history() -> None:
    """If the readings table is empty, seed 24h of synthetic history once at boot."""
    p = await get_pool()
    async with p.acquire() as conn:
        n = await conn.fetchval("SELECT COUNT(*) FROM sensors.readings")
        if n and n > 0:
            return
        sensors = await conn.fetch("SELECT id, sensor_type FROM sensors.sensors")
        now = datetime.now(timezone.utc)
        for s in sensors:
            base = _baseline(s["sensor_type"])
            for i in range(96):  # every 15 min over 24h
                ts = now - timedelta(minutes=(96 - i) * 15)
                value = max(0.0, base["mean"] + random.uniform(-base["noise"], base["noise"]))
                await conn.execute(
                    "INSERT INTO sensors.readings (sensor_id, value, measured_at) VALUES ($1,$2,$3)",
                    s["id"], value, ts,
                )


async def _ingest_loop() -> None:
    """Continuously append fresh readings so the dashboard always shows live data."""
    interval = int(os.getenv("INGEST_INTERVAL_SEC", "10"))
    while True:
        try:
            p = await get_pool()
            async with p.acquire() as conn:
                sensors = await conn.fetch("SELECT id, sensor_type FROM sensors.sensors")
                now = datetime.now(timezone.utc)
                for s in sensors:
                    base = _baseline(s["sensor_type"])
                    value = max(0.0, base["mean"] + random.uniform(-base["noise"], base["noise"]))
                    await conn.execute(
                        "INSERT INTO sensors.readings (sensor_id, value, measured_at) VALUES ($1,$2,$3)",
                        s["id"], value, now,
                    )
                # prune very old data to keep the table bounded
                await conn.execute(
                    "DELETE FROM sensors.readings WHERE measured_at < now() - INTERVAL '7 days'"
                )
        except asyncio.CancelledError:
            return
        except Exception:
            pass
        await asyncio.sleep(interval)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "data-service"}


# ===== Zones =====
@app.get("/zones", response_model=list[ZoneOut])
async def list_zones(_: dict = Depends(auth_required)):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, code, name, description FROM sensors.zones ORDER BY id"
        )
    return [dict(r) for r in rows]


@app.post("/zones", response_model=ZoneOut)
async def create_zone(z: ZoneIn, _: dict = Depends(role_required("admin", "engineer"))):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO sensors.zones (code, name, description)
               VALUES ($1,$2,$3) RETURNING id, code, name, description""",
            z.code, z.name, z.description,
        )
    return dict(row)


@app.put("/zones/{zone_id}", response_model=ZoneOut)
async def update_zone(zone_id: int, z: ZoneIn, _: dict = Depends(role_required("admin", "engineer"))):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE sensors.zones
                  SET code=$1, name=$2, description=$3
                WHERE id=$4
            RETURNING id, code, name, description""",
            z.code, z.name, z.description, zone_id,
        )
    if not row:
        raise HTTPException(404, "Зону не знайдено")
    return dict(row)


@app.delete("/zones/{zone_id}")
async def delete_zone(zone_id: int, _: dict = Depends(role_required("admin"))):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM sensors.zones WHERE id=$1", zone_id)
    return {"deleted": zone_id}


# ===== Sensors =====
@app.get("/sensors", response_model=list[SensorOut])
async def list_sensors(zone_id: Optional[int] = None, _: dict = Depends(auth_required)):
    p = await get_pool()
    sql = "SELECT id, zone_id, code, sensor_type, unit FROM sensors.sensors"
    args = []
    if zone_id is not None:
        sql += " WHERE zone_id=$1"
        args.append(zone_id)
    sql += " ORDER BY id"
    async with p.acquire() as conn:
        rows = await conn.fetch(sql, *args)
    return [dict(r) for r in rows]


@app.post("/sensors", response_model=SensorOut)
async def create_sensor(s: SensorIn, _: dict = Depends(role_required("admin", "engineer"))):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO sensors.sensors (zone_id, code, sensor_type, unit)
               VALUES ($1,$2,$3,$4)
               RETURNING id, zone_id, code, sensor_type, unit""",
            s.zone_id, s.code, s.sensor_type, s.unit,
        )
    return dict(row)


@app.put("/sensors/{sensor_id}", response_model=SensorOut)
async def update_sensor(sensor_id: int, s: SensorIn, _: dict = Depends(role_required("admin", "engineer"))):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE sensors.sensors
                  SET zone_id=$1, code=$2, sensor_type=$3, unit=$4
                WHERE id=$5
            RETURNING id, zone_id, code, sensor_type, unit""",
            s.zone_id, s.code, s.sensor_type, s.unit, sensor_id,
        )
    if not row:
        raise HTTPException(404, "Датчик не знайдено")
    return dict(row)


@app.delete("/sensors/{sensor_id}")
async def delete_sensor(sensor_id: int, _: dict = Depends(role_required("admin"))):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM sensors.sensors WHERE id=$1", sensor_id)
    return {"deleted": sensor_id}


# ===== Readings =====
@app.get("/readings", response_model=list[ReadingOut])
async def list_readings(
    sensor_id: Optional[int] = None,
    zone_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(500, ge=1, le=10000),
    _: dict = Depends(auth_required),
):
    p = await get_pool()
    conds = ["r.measured_at >= now() - ($1 || ' hours')::interval"]
    args: list = [str(hours)]
    if sensor_id is not None:
        args.append(sensor_id)
        conds.append(f"r.sensor_id = ${len(args)}")
    if zone_id is not None:
        args.append(zone_id)
        conds.append(f"s.zone_id = ${len(args)}")
    if sensor_type is not None:
        args.append(sensor_type)
        conds.append(f"s.sensor_type = ${len(args)}")
    sql = f"""SELECT r.id, r.sensor_id, r.value, r.measured_at
              FROM sensors.readings r
              JOIN sensors.sensors s ON s.id = r.sensor_id
              WHERE {' AND '.join(conds)}
              ORDER BY r.measured_at DESC
              LIMIT {limit}"""
    async with p.acquire() as conn:
        rows = await conn.fetch(sql, *args)
    return [dict(r) for r in rows]


@app.post("/readings", response_model=ReadingOut)
async def create_reading(r: ReadingIn, _: dict = Depends(auth_required)):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO sensors.readings (sensor_id, value, measured_at)
               VALUES ($1, $2, COALESCE($3, now()))
               RETURNING id, sensor_id, value, measured_at""",
            r.sensor_id, r.value, r.measured_at,
        )
    return dict(row)


@app.get("/readings/latest")
async def latest_readings(_: dict = Depends(auth_required)):
    """Latest reading per sensor with zone metadata."""
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """SELECT DISTINCT ON (s.id)
                    s.id AS sensor_id, s.code AS sensor_code, s.sensor_type, s.unit,
                    z.id AS zone_id, z.code AS zone_code, z.name AS zone_name,
                    r.value, r.measured_at
               FROM sensors.sensors s
               LEFT JOIN sensors.zones z ON z.id = s.zone_id
               LEFT JOIN sensors.readings r ON r.sensor_id = s.id
               ORDER BY s.id, r.measured_at DESC NULLS LAST"""
        )
    return [dict(r) for r in rows]


# ===== Simulation =====
@app.post("/simulate")
async def simulate(
    points_per_sensor: int = Query(20, ge=1, le=500),
    _: dict = Depends(role_required("admin", "engineer")),
):
    """Generate synthetic readings for every registered sensor."""
    p = await get_pool()
    now = datetime.now(timezone.utc)
    inserted = 0
    async with p.acquire() as conn:
        sensors = await conn.fetch(
            "SELECT id, sensor_type FROM sensors.sensors"
        )
        for s in sensors:
            base = _baseline(s["sensor_type"])
            for i in range(points_per_sensor):
                ts = now - timedelta(minutes=(points_per_sensor - i) * 5)
                noise = random.uniform(-base["noise"], base["noise"])
                value = max(0.0, base["mean"] + noise)
                await conn.execute(
                    """INSERT INTO sensors.readings (sensor_id, value, measured_at)
                       VALUES ($1,$2,$3)""",
                    s["id"], value, ts,
                )
                inserted += 1
    return {"inserted": inserted, "sensors": len(sensors)}


def _baseline(sensor_type: str) -> dict:
    return {
        "radiation":   {"mean": 8.0,    "noise": 2.5},
        "pressure":    {"mean": -120.0, "noise": 25.0},
        "airflow":     {"mean": 18000.0,"noise": 2500.0},
        "temperature": {"mean": 22.0,   "noise": 1.5},
    }.get(sensor_type, {"mean": 1.0, "noise": 0.1})
