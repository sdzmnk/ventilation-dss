import asyncio
import csv
import json
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

DATASET_CSV = os.getenv("VENT_DATASET_CSV", "/data/ventilation_history.csv")
BASELINES_JSON = os.getenv("VENT_BASELINES_JSON", "/data/ventilation_baselines.json")

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

app = FastAPI(title="Data Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pool: Optional[asyncpg.Pool] = None

# In-memory cache populated at startup from the CSV / JSON the container mounts.
_DATASET: list[dict] = []
_BASELINES: dict[str, dict] = {}
_DATASET_CURSOR = 0


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
    _load_dataset()
    await get_pool()
    await _ensure_topology()
    await _seed_history()
    global _ingest_task
    _ingest_task = asyncio.create_task(_ingest_loop())


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _ingest_task:
        _ingest_task.cancel()
    if pool:
        await pool.close()


def _load_dataset() -> None:
    """Read the CSV + baseline-stats files mounted into the container.

    The CSV is the cleaned 2020-2024 history (one row per snapshot, columns
    are normalized ASCII sensor keys + a `ts` timestamp). The baselines JSON
    holds per-channel mean/std/percentiles used by the live-ingest loop to
    add realistic jitter when we run out of CSV rows.
    """
    global _DATASET, _BASELINES
    if os.path.exists(DATASET_CSV):
        with open(DATASET_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            _DATASET = list(reader)
        print(f"[data-service] loaded {len(_DATASET)} rows from {DATASET_CSV}")
    else:
        print(f"[data-service] dataset CSV not found at {DATASET_CSV} — fallback synthetic")

    if os.path.exists(BASELINES_JSON):
        with open(BASELINES_JSON, encoding="utf-8") as f:
            _BASELINES = json.load(f)
        print(f"[data-service] loaded baselines for {len(_BASELINES)} channels")


def _row_value(row: dict, sensor_type: str) -> Optional[float]:
    raw = row.get(sensor_type)
    if raw in (None, "", "nan", "NaN"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _baseline(sensor_type: str) -> dict:
    """Statistics used when no CSV value is available."""
    if sensor_type in _BASELINES:
        b = _BASELINES[sensor_type]
        # use stddev as noise band, but cap it so the live signal does not
        # walk too far from the median
        std = max(0.001, float(b.get("std", 0.0)))
        return {"mean": float(b["p50"]), "noise": std * 0.4}
    # fall back to safe defaults for unknown channels
    return {"mean": 1.0, "noise": 0.1}


# Canonical topology — a single source of truth.
# `_ensure_topology` syncs this against the DB on startup so a stale
# `pgdata` volume from a previous schema gets healed without manual reset.
TOPOLOGY = [
    # (zone_code, zone_name, zone_desc, sensor_code, sensor_type, sensor_name, unit)
    ("ENV",  "Зовнішнє середовище",          "Метеопараметри: вітер, густина повітря",
        "ENV-WSP",   "wind_speed",     "Швидкість вітру",       "м/с"),
    ("ENV",  None, None,
        "ENV-WDIR",  "wind_direction", "Напрям вітру",          "°"),
    ("ENV",  None, None,
        "ENV-RHO",   "air_density",    "Густина повітря",       "кг/м³"),

    ("KP",   "Герметична зона (КП)",  "Тиск і витрата у герметичній зоні (контайнменті)",
        "KP-PRES",   "pressure_kp",    "Тиск у герметичній зоні (КП)", "Па"),
    ("KP",   None, None,
        "KP-FLOW-IN","flow_kp_in",     "Приплив повітря КП+",   "тис. м³/год"),

    ("OO",   "Зона обстеження-обслуговування (ОО)", "Тиск і витрати у зоні ОО",
        "OO-PRES",   "pressure_oo",    "Тиск у зоні ОО",         "Па"),
    ("OO",   None, None,
        "OO-FLOW-OUT","flow_oo_out",   "Витяжка ОО−",            "тис. м³/год"),
    ("OO",   None, None,
        "OO-FLOW-IN","flow_oo_in",     "Приплив ОО+",            "тис. м³/год"),

    ("DIFF", "Перепади тисків",       "Перепади між зонами КП, ОО, ОС у різних точках",
        "DP-KP-OS",     "dp_kp_os",     "Перепад КП − ОС",       "Па"),
    ("DIFF", None, None,
        "DP-OO-OS-8",   "dp_oo_os_8",   "Перепад ОО − ОС (8-й)", "Па"),
    ("DIFF", None, None,
        "DP-OO-OS-9",   "dp_oo_os_9",   "Перепад ОО − ОС (BU 9-й)", "Па"),
    ("DIFF", None, None,
        "DP-KP-OO",     "dp_kp_oo",     "Перепад КП − ОО",       "Па"),
    ("DIFF", None, None,
        "DP-KP-OO-BY",  "dp_kp_oo_by",  "Перепад КП − ОО (BY 11-10)", "Па"),
    ("DIFF", None, None,
        "DP-KP-OO-BZ",  "dp_kp_oo_bz",  "Перепад КП − ОО (BZ_8)", "Па"),
    ("DIFF", None, None,
        "DP-KP-OO-CA",  "dp_kp_oo_ca",  "Перепад КП − ОО (CA)", "Па"),

    ("GU",   "Гермоустановка",        "Тиски на стінках, у зазорах, та СКО",
        "GU-P-W",     "gu_pressure_west_wall",  "Тиск ГУ — західна стінка",     "Па"),
    ("GU",   None, None,
        "GU-P-E",     "gu_pressure_east_wall",  "Тиск ГУ — східна стінка",      "Па"),
    ("GU",   None, None,
        "GU-P-CYL",   "gu_pressure_cyl_wall",   "Тиск ГУ — циліндрична стінка", "Па"),
    ("GU",   None, None,
        "GU-P-WGAP",  "gu_pressure_west_gap",   "Тиск ГУ — західний зазор",     "Па"),
    ("GU",   None, None,
        "GU-P-EGAP",  "gu_pressure_east_gap",   "Тиск ГУ — східний зазор",      "Па"),
    ("GU",   None, None,
        "GU-P-VSRO",  "gu_pressure_vsro",       "Тиск ГУ — ВСРО",               "Па"),
    ("GU",   None, None,
        "GU-S-008",   "gu_sigma_008",           "СКО тиск 008p (BQ)",           "Па"),
    ("GU",   None, None,
        "GU-S-009",   "gu_sigma_009",           "СКО тиск 009p (BR)",           "Па"),
    ("GU",   None, None,
        "GU-S-KPOS",  "gu_sigma_kp_os",         "СКО тиск КП-ОС (BS)",          "Па"),
]


async def _ensure_topology() -> None:
    """Idempotently sync zones+sensors with TOPOLOGY.

    This runs on every startup so:
    - a fresh `pgdata` volume picks up the seed via init.sql, then this is a no-op
    - an EXISTING volume from an earlier schema (e.g. radiation/pressure/airflow)
      gets healed: missing zones/sensors are created, obsolete sensors with
      sensor_type not in TOPOLOGY are removed (their readings cascade)
    """
    p = await get_pool()
    valid_types = {row[4] for row in TOPOLOGY}

    async with p.acquire() as conn:
        # zones
        for row in TOPOLOGY:
            zone_code, zone_name, zone_desc = row[0], row[1], row[2]
            if zone_name is None:
                continue
            await conn.execute(
                """INSERT INTO sensors.zones (code, name, description)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (code) DO UPDATE
                       SET name = EXCLUDED.name,
                           description = EXCLUDED.description""",
                zone_code, zone_name, zone_desc,
            )

        # sensors
        for row in TOPOLOGY:
            zone_code, _, _, sensor_code, sensor_type, _name, unit = row
            zone_id = await conn.fetchval(
                "SELECT id FROM sensors.zones WHERE code = $1", zone_code
            )
            await conn.execute(
                """INSERT INTO sensors.sensors (zone_id, code, sensor_type, unit)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (code) DO UPDATE
                       SET zone_id = EXCLUDED.zone_id,
                           sensor_type = EXCLUDED.sensor_type,
                           unit = EXCLUDED.unit""",
                zone_id, sensor_code, sensor_type, unit,
            )

        # Drop obsolete sensors (e.g. old radiation/pressure/airflow/temperature)
        # so they no longer pollute /readings/latest and /analytic/stats.
        # Cascading FK on sensors.readings(sensor_id) cleans the readings.
        await conn.execute(
            "DELETE FROM sensors.sensors WHERE sensor_type <> ALL($1::text[])",
            list(valid_types),
        )

        # Make sure the unit column is wide enough for the long names we use
        # (legacy schema had VARCHAR(32); new units fit but be defensive).
        try:
            await conn.execute(
                "ALTER TABLE sensors.sensors ALTER COLUMN sensor_type TYPE VARCHAR(64)"
            )
        except Exception:
            pass


async def _seed_history() -> None:
    """Seed the readings table from the CSV with timestamps mapped to today.

    Runs whenever the table is empty OR contains less than ~24h of data
    aligned with the current sensor topology. Stale data from previous
    schemas (already pruned by `_ensure_topology`) does not count toward
    the threshold.
    """
    p = await get_pool()
    async with p.acquire() as conn:
        n = await conn.fetchval(
            """SELECT COUNT(*) FROM sensors.readings r
               JOIN sensors.sensors s ON s.id = r.sensor_id
               WHERE r.measured_at >= now() - INTERVAL '24 hours'"""
        )
        # 24 sensors × at least 100 fresh rows ≈ a populated dashboard
        if n and n > 24 * 100:
            print(f"[data-service] readings up to date ({n} rows in last 24h) — skipping seed")
            return

        sensors = await conn.fetch("SELECT id, sensor_type FROM sensors.sensors")
        sensor_by_type = {s["sensor_type"]: s["id"] for s in sensors}

        # Clean stale readings tied to this topology to avoid the "step
        # function" we saw on the trend chart when old + new data mix.
        await conn.execute(
            """DELETE FROM sensors.readings
               WHERE measured_at < now() - INTERVAL '24 hours'"""
        )

        if not _DATASET:
            now = datetime.now(timezone.utc)
            for s in sensors:
                base = _baseline(s["sensor_type"])
                for i in range(96):
                    ts = now - timedelta(minutes=(96 - i) * 15)
                    value = base["mean"] + random.uniform(-base["noise"], base["noise"])
                    await conn.execute(
                        "INSERT INTO sensors.readings (sensor_id, value, measured_at) VALUES ($1,$2,$3)",
                        s["id"], value, ts,
                    )
            return

        # Spread 288 CSV snapshots evenly across the last 24h so the
        # timeline always looks current.
        seed_rows = _DATASET[-288:]
        now = datetime.now(timezone.utc)
        step = timedelta(hours=24) / max(1, len(seed_rows))

        for i, row in enumerate(seed_rows):
            ts = now - (len(seed_rows) - i) * step
            for sensor_type, sensor_id in sensor_by_type.items():
                v = _row_value(row, sensor_type)
                if v is None:
                    base = _baseline(sensor_type)
                    v = base["mean"] + random.uniform(-base["noise"], base["noise"])
                await conn.execute(
                    "INSERT INTO sensors.readings (sensor_id, value, measured_at) VALUES ($1,$2,$3)",
                    sensor_id, v, ts,
                )
        print(f"[data-service] seeded {len(seed_rows)} snapshots × {len(sensor_by_type)} sensors")


async def _ingest_loop() -> None:
    """Continuously walk through the CSV, replaying real readings as live data.

    Each tick advances one row in the CSV; once we run out we wrap back to
    the start. A small per-channel jitter (proportional to the historical
    standard deviation) keeps successive cycles visually distinct.
    """
    global _DATASET_CURSOR
    interval = int(os.getenv("INGEST_INTERVAL_SEC", "10"))

    while True:
        try:
            p = await get_pool()
            async with p.acquire() as conn:
                sensors = await conn.fetch("SELECT id, sensor_type FROM sensors.sensors")
                now = datetime.now(timezone.utc)

                row = _DATASET[_DATASET_CURSOR] if _DATASET else None
                _DATASET_CURSOR = (_DATASET_CURSOR + 1) % max(1, len(_DATASET))

                for s in sensors:
                    sensor_type = s["sensor_type"]
                    base = _baseline(sensor_type)
                    if row is not None:
                        v = _row_value(row, sensor_type)
                        if v is None:
                            v = base["mean"]
                        # gentle noise so identical CSV passes do not look
                        # like a step function
                        v = v + random.uniform(-base["noise"] * 0.25,
                                                base["noise"] * 0.25)
                    else:
                        v = base["mean"] + random.uniform(-base["noise"], base["noise"])

                    await conn.execute(
                        "INSERT INTO sensors.readings (sensor_id, value, measured_at) VALUES ($1,$2,$3)",
                        s["id"], v, now,
                    )

                # keep the table bounded
                await conn.execute(
                    "DELETE FROM sensors.readings WHERE measured_at < now() - INTERVAL '7 days'"
                )
        except asyncio.CancelledError:
            return
        except Exception as e:
            print(f"[data-service] ingest error: {e}")
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
    """Generate readings for every registered sensor by replaying the dataset.

    Like the live-ingest loop, but bulk: pull `points_per_sensor` consecutive
    rows from the CSV starting at the current cursor and write them with
    timestamps spread across the last few hours.
    """
    global _DATASET_CURSOR
    p = await get_pool()
    now = datetime.now(timezone.utc)
    inserted = 0

    rows_to_use = []
    if _DATASET:
        for _ in range(points_per_sensor):
            rows_to_use.append(_DATASET[_DATASET_CURSOR])
            _DATASET_CURSOR = (_DATASET_CURSOR + 1) % len(_DATASET)
    step = timedelta(minutes=5)

    async with p.acquire() as conn:
        sensors = await conn.fetch(
            "SELECT id, sensor_type FROM sensors.sensors"
        )
        for i in range(points_per_sensor):
            ts = now - (points_per_sensor - i) * step
            row = rows_to_use[i] if rows_to_use else None
            for s in sensors:
                base = _baseline(s["sensor_type"])
                if row is not None:
                    v = _row_value(row, s["sensor_type"])
                    if v is None:
                        v = base["mean"]
                else:
                    v = base["mean"] + random.uniform(-base["noise"], base["noise"])
                await conn.execute(
                    """INSERT INTO sensors.readings (sensor_id, value, measured_at)
                       VALUES ($1,$2,$3)""",
                    s["id"], v, ts,
                )
                inserted += 1
    return {"inserted": inserted, "sensors": len(sensors)}
