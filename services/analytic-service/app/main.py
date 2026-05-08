"""Analytic service.

Replaces the previous radiation/pressure/airflow/temperature logic with
predictions calibrated on the real 2020-2024 ventilation dataset.
The relevant safety-critical channels are:

  * pressure_kp            — тиск у герметичній зоні (КП)
  * pressure_oo            — тиск у приміщенні ОО
  * dp_kp_oo               — перепад КП-ОО (повинен бути позитивним)
  * flow_kp_in             — витрата КП+ (приплив у КП)
  * flow_oo_out            — витрата ОО- (витяжка ОО)
  * wind_speed             — зовнішній вітер (вплив на герметичність)
  * gu_pressure_*          — тиски на стінках гермоустановки
                             (відхилення = деформація / розгерметизація)
  * gu_sigma_*             — СКО тиску, прокси-показник турбулентності

Defaults / thresholds are derived from the dataset baselines:
  see /data/ventilation_baselines.json (mounted from db/ventilation_baselines.json).
"""
import json
import math
import os
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import jwt
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from scipy.optimize import minimize

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
BASELINES_JSON = os.getenv("VENT_BASELINES_JSON", "/data/ventilation_baselines.json")

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

app = FastAPI(title="Analytic Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pool: Optional[asyncpg.Pool] = None
_BASELINES: dict[str, dict] = {}


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


# ===== Models =====
class OptimizationIn(BaseModel):
    method: str = Field("scipy", description="scipy | grid")
    fan_power_kw: float = Field(15.0, gt=0)
    energy_cost_kwh: float = Field(0.12, ge=0)
    pressure_kp_target: float = Field(-10.0, description="Цільовий тиск КП, Па")
    pressure_oo_target: float = Field(-17.0, description="Цільовий тиск ОО, Па")
    dp_kp_oo_min: float = Field(2.0, description="Мінімальний перепад КП-ОО, Па")
    flow_kp_min: float = Field(10.0, gt=0, description="тис. м³/год")
    flow_kp_max: float = Field(28.0, gt=0)
    flow_oo_min: float = Field(15.0, gt=0)
    flow_oo_max: float = Field(40.0, gt=0)
    filter_efficiency: float = Field(0.999, gt=0, le=1)
    current_wind_speed: float = Field(2.0, ge=0)


class OptimizationResult(BaseModel):
    id: Optional[int] = None
    method: str
    optimal_flow_kp: float
    optimal_flow_oo: float
    optimal_fan_load: float
    expected_pressure_kp: float
    expected_pressure_oo: float
    expected_dp_kp_oo: float
    energy_kw: float
    energy_cost_per_hour: float
    safety_margin: float
    status: str
    iterations: int


class StatsOut(BaseModel):
    sensor_type: str
    count: int
    mean: float
    min: float
    max: float
    p95: float


# ===== Lifecycle =====
@app.on_event("startup")
async def _startup() -> None:
    _load_baselines()
    global THRESHOLDS
    THRESHOLDS = _derive_thresholds()
    print(f"[analytic-service] derived thresholds for {len(THRESHOLDS)} of "
          f"{len(CHANNEL_WEIGHTS)} weighted channels")
    await get_pool()


@app.on_event("shutdown")
async def _shutdown() -> None:
    if pool:
        await pool.close()


def _load_baselines() -> None:
    global _BASELINES
    if os.path.exists(BASELINES_JSON):
        with open(BASELINES_JSON, encoding="utf-8") as f:
            _BASELINES = json.load(f)
        print(f"[analytic-service] loaded baselines for {len(_BASELINES)} channels")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "analytic-service"}


# ===== Predict =====
# Per-channel weight in the composite danger score. Weights reflect
# operational priority: dp_kp_oo (контайнмент — критичний показник
# герметичності) gets the largest single share, secondary diff channels
# vote together, GU walls/gaps show containment integrity, σ channels
# capture turbulence. Total ≈ 1.00.
CHANNEL_WEIGHTS = {
    # primary safety channels
    "dp_kp_oo":              0.13,
    "pressure_kp":           0.10,
    "pressure_oo":           0.08,
    "flow_kp_in":            0.06,
    "flow_oo_out":           0.06,

    # secondary differential channels
    "dp_kp_os":              0.04,
    "dp_oo_os_8":            0.04,
    "dp_oo_os_9":            0.04,
    "dp_kp_oo_by":           0.04,
    "dp_kp_oo_bz":           0.04,
    "dp_kp_oo_ca":           0.04,
    "flow_oo_in":            0.02,

    # GU containment integrity
    "gu_pressure_west_wall": 0.04,
    "gu_pressure_east_wall": 0.04,
    "gu_pressure_cyl_wall":  0.03,
    "gu_pressure_west_gap":  0.03,
    "gu_pressure_east_gap":  0.03,
    "gu_pressure_vsro":      0.03,

    # turbulence proxies (СКО тиску)
    "gu_sigma_008":          0.02,
    "gu_sigma_009":          0.02,
    "gu_sigma_kp_os":        0.02,

    # environmental
    "wind_speed":            0.04,
    # wind_direction excluded (circular variable, no "danger zone")
    # air_density excluded (essentially constant in our dataset)
}
# Channels we accept on /analytic/predict — superset of CHANNEL_WEIGHTS
# (extras can still be passed for /sensors page consistency, just don't
# affect the score).
KNOWN_CHANNELS = set(CHANNEL_WEIGHTS) | {"wind_direction", "air_density"}

# Thresholds (warn_lo, warn_hi, crit_lo, crit_hi) per channel.
# Auto-derived on startup from baselines so the model stays in sync with
# the dataset; can be overridden per channel via THRESHOLD_OVERRIDES.
THRESHOLDS: dict[str, tuple[float, float, float, float]] = {}

THRESHOLD_OVERRIDES: dict[str, tuple[float, float, float, float]] = {
    # dp_kp_oo: business rule — must stay positive. p05 in the dataset
    # is already negative due to historical outages, so we tighten the
    # warn band manually.
    "dp_kp_oo": (0.0, 22.0, -15.0, 35.0),
    # wind speed has no negative side
    "wind_speed": (0.0, 7.0, 0.0, 14.0),
}


def _derive_thresholds() -> dict:
    """warn = [p05 − 0.25σ, p95 + 0.25σ]; crit = [p05 − 3σ, p95 + 3σ]."""
    out: dict[str, tuple[float, float, float, float]] = {}
    for k in CHANNEL_WEIGHTS:
        if k in THRESHOLD_OVERRIDES:
            out[k] = THRESHOLD_OVERRIDES[k]
            continue
        b = _BASELINES.get(k)
        if not b:
            continue
        std = max(0.5, float(b.get("std", 1.0)))
        p05 = float(b.get("p05", b.get("min", 0.0)))
        p95 = float(b.get("p95", b.get("max", 0.0)))
        warn_lo = p05 - 0.25 * std
        warn_hi = p95 + 0.25 * std
        crit_lo = p05 - 3.0 * std
        crit_hi = p95 + 3.0 * std
        out[k] = (warn_lo, warn_hi, crit_lo, crit_hi)
    return out


def _channel_score(value: float, t: tuple, nominal: Optional[float] = None) -> float:
    """Return 0..1 danger score for a sensor reading.

    Smooth profile (no flat zero plateau):
      - 0.00 at `nominal` (defaults to dataset median; fallback = centre of warn band)
      - rises quadratically (asymmetric) to 0.20 at the nearer warn boundary
      - rises linearly from 0.20 to 1.00 between warn and crit boundaries
      - clipped at 1.0 beyond the crit boundary

    Asymmetry matters: e.g. `flow_oo_in` has p50=0 but warn = (0, 3) so the
    geometric centre of the safe band (1.5) is *wrong* — p50=0 is the real
    nominal. We pass the dataset median in via `nominal` to avoid that bug.

    The previous version returned exactly 0.0 anywhere inside the safe
    zone, which made the composite collapse to 0 and the OK confidence
    pin at 100% on every snapshot.
    """
    warn_lo, warn_hi, crit_lo, crit_hi = t
    if nominal is None:
        nominal = (warn_lo + warn_hi) / 2.0
    # clamp nominal into the safe zone in case baselines are pathological
    nominal = max(warn_lo, min(warn_hi, nominal))

    if warn_lo <= value <= warn_hi:
        if value >= nominal:
            half = max(1e-6, warn_hi - nominal)
        else:
            half = max(1e-6, nominal - warn_lo)
        return 0.20 * ((abs(value - nominal) / half) ** 2)
    if value < warn_lo:
        if value <= crit_lo:
            return 1.0
        return 0.20 + 0.80 * (warn_lo - value) / max(1e-6, warn_lo - crit_lo)
    # value > warn_hi
    if value >= crit_hi:
        return 1.0
    return 0.20 + 0.80 * (value - warn_hi) / max(1e-6, crit_hi - warn_hi)


# Aleatoric uncertainty floor — even with every monitored channel at
# its nominal centre we never claim 100% confidence:
#   * sensors drift / age / get noisier over time
#   * historical OK regimes still contained occasional surprises
#   * the model is statistical, not physical
NOISE_FLOOR = 0.06


@app.get("/analytic/predict")
async def predict(
    request: Request,
    hours:   int = Query(24, ge=1, le=720),
    _: dict = Depends(auth_required),
):
    """Classify ventilation system state from any subset of the real channels.

    Accepts ALL channels in CHANNEL_WEIGHTS as optional query parameters
    (e.g. `?pressure_kp=-12&dp_kp_oo=8&gu_sigma_008=0.5`). Channels not
    provided are filled from the average of the last `hours` readings.
    Channels with no DB readings fall back to the dataset median.
    """
    given: dict[str, float] = {}
    missing: list[str] = []
    for k in CHANNEL_WEIGHTS:
        raw = request.query_params.get(k)
        if raw is None:
            missing.append(k)
            continue
        try:
            given[k] = float(raw)
        except ValueError:
            raise HTTPException(400, f"параметр {k} повинен бути числом")

    if missing:
        p = await get_pool()
        async with p.acquire() as conn:
            rows = await conn.fetch(
                """SELECT s.sensor_type, AVG(r.value)::float8 AS mean
                   FROM sensors.readings r
                   JOIN sensors.sensors s ON s.id = r.sensor_id
                   WHERE r.measured_at >= now() - ($1 || ' hours')::interval
                   GROUP BY s.sensor_type""",
                str(hours),
            )
        db = {r["sensor_type"]: float(r["mean"]) for r in rows}
        for k in missing:
            if k in db:
                given[k] = db[k]
            elif k in _BASELINES:
                given[k] = float(_BASELINES[k].get("p50", 0.0))
            else:
                # channel has no reading and no baseline — assume nominal-centred
                t = THRESHOLDS.get(k)
                given[k] = (t[0] + t[1]) / 2.0 if t else 0.0

    # Per-channel danger score (only channels that have thresholds).
    # `nominal` = dataset median so an asymmetric safe band is handled
    # correctly (e.g. flow_oo_in: p50=0 but warn=(0, 3)).
    scores = {
        k: _channel_score(
            float(given[k]),
            THRESHOLDS[k],
            nominal=float(_BASELINES.get(k, {}).get("p50",
                          (THRESHOLDS[k][0] + THRESHOLDS[k][1]) / 2.0)),
        )
        for k in CHANNEL_WEIGHTS if k in THRESHOLDS
    }

    raw_composite = sum(scores[k] * CHANNEL_WEIGHTS[k] for k in scores)
    # Severity is the max of:
    #   * weighted composite (many small drifts)
    #   * 0.7 × max single-channel score (one channel in trouble)
    # so a single CRITICAL channel can't be drowned out by 21 nominal ones.
    max_score = max(scores.values()) if scores else 0.0
    severity = max(raw_composite, 0.7 * max_score)
    # Apply the noise floor so OK confidence saturates around 94%, never 100%
    composite = min(1.0, max(NOISE_FLOOR, severity))

    # Probabilities — always sum to 1
    if composite < 0.35:
        p_ok       = 1.0 - composite
        p_warning  = composite / 2.0
        p_critical = composite / 2.0
        status = "OK"
    elif composite < 0.65:
        t = (composite - 0.35) / 0.30
        p_ok       = 1.0 - composite
        p_warning  = composite * (0.5 + 0.5 * t)
        p_critical = composite * (0.5 - 0.5 * t)
        status = "WARNING" if p_warning > p_ok else "OK"
    else:
        t = (composite - 0.65) / 0.35
        p_ok       = 1.0 - composite
        p_critical = composite * (0.5 + 0.5 * t)
        p_warning  = composite * (0.5 - 0.5 * t)
        status = "CRITICAL" if p_critical > p_ok else "WARNING"

    confidence = {"OK": p_ok, "WARNING": p_warning, "CRITICAL": p_critical}[status]
    risk_score = round((1.0 - composite) * 100.0, 1)

    return {
        "prediction_data": {
            "status": status,
            "risk_score": risk_score,
            "confidence": round(confidence, 4),
            "probabilities": {
                "CRITICAL": round(p_critical, 4),
                "OK":       round(p_ok,       4),
                "WARNING":  round(p_warning,  4),
            },
            "channel_scores": {k: round(v, 3) for k, v in scores.items()},
        },
        "inputs": {k: round(float(v), 3) for k, v in given.items()},
        "recommendation": _build_recommendation(status, confidence, given, scores),
    }


def _build_recommendation(
    status: str,
    confidence: float,
    v: dict,
    scores: dict,
) -> str:
    conf_pct = f"{confidence * 100:.2f}%"
    issues = _describe_issues(v, scores)

    if status == "OK":
        if not issues:
            issues = ["незначні коливання тиску та витрат у межах експлуатаційної норми"]
        return (
            f"Вентиляційна система працює в межах норми (впевненість {conf_pct}). "
            f"Перепад КП-ОО {v['dp_kp_oo']:.1f} Па, тиск КП {v['pressure_kp']:.1f} Па, "
            f"тиск ОО {v['pressure_oo']:.1f} Па. "
            f"Зауваження: {'; '.join(issues)}.\n\n"
            "Рекомендація оператору: продовжувати штатний моніторинг кожні 30 хвилин, "
            "контролювати показання СКО тиску ГУ та зовнішній вітер. "
            "У разі стійкого зменшення перепаду КП-ОО — перевірити стан фільтрів Ф-101/Ф-102 "
            "та режим роботи припливних вентиляторів."
        )

    if status == "WARNING":
        return (
            f"Виявлено відхилення параметрів (впевненість {conf_pct}). "
            f"Проблеми: {'; '.join(issues) if issues else 'комбінований дрейф кількох каналів'}.\n\n"
            "Необхідні дії:\n"
            "1. Перевірити стан HEPA-фільтру Ф-102 — типова причина зменшення перепаду КП-ОО.\n"
            "2. Скоригувати завантаження вентилятора М-1 (приплив КП) на ±10% та перевірити стабілізацію тиску КП.\n"
            "3. Збільшити частоту реєстрації показань ГУ Тиск (західна/східна стінки) до 1 хв.\n"
            "4. Повідомити інженерну службу та підготувати резервний вентилятор М-3."
        )

    # CRITICAL
    return (
        f"КРИТИЧНА СИТУАЦІЯ: вентиляційна система потребує негайного втручання (впевненість {conf_pct}). "
        f"Критичні відхилення: {'; '.join(issues) if issues else 'низка параметрів за межами безпечних діапазонів'}.\n\n"
        "Аварійне реагування:\n"
        "• Активувати аварійний режим витяжної вентиляції (М-1 + М-2 + М-3 одночасно).\n"
        "• Закрити герметичні засувки К-1/К-2 у разі від'ємного перепаду КП-ОО — це прямий ризик зворотного потоку.\n"
        "• Якщо перевищено |тиск ГУ| на стінках — призупинити будь-які роботи у гермозоні до стабілізації.\n"
        "• Повідомити начальника зміни. Відновлення штатного режиму — лише після підтвердження інженерною службою."
    )


# Human-readable label + unit for each channel (used in recommendations).
CHANNEL_LABELS = {
    "pressure_kp":           ("тиск КП",                    "Па"),
    "pressure_oo":           ("тиск ОО",                    "Па"),
    "dp_kp_oo":              ("перепад КП-ОО",              "Па"),
    "dp_kp_os":              ("перепад КП-ОС",              "Па"),
    "dp_oo_os_8":            ("перепад ОО-ОС (8-й)",        "Па"),
    "dp_oo_os_9":            ("перепад ОО-ОС (BU 9-й)",     "Па"),
    "dp_kp_oo_by":           ("перепад КП-ОО (BY 11-10)",   "Па"),
    "dp_kp_oo_bz":           ("перепад КП-ОО (BZ_8)",       "Па"),
    "dp_kp_oo_ca":           ("перепад КП-ОО (CA)",         "Па"),
    "flow_kp_in":            ("витрата КП+",                "тис. м³/год"),
    "flow_oo_out":           ("витрата ОО−",                "тис. м³/год"),
    "flow_oo_in":            ("витрата ОО+",                "тис. м³/год"),
    "wind_speed":            ("швидкість вітру",            "м/с"),
    "gu_pressure_west_wall": ("тиск ГУ — західна стінка",   "Па"),
    "gu_pressure_east_wall": ("тиск ГУ — східна стінка",    "Па"),
    "gu_pressure_cyl_wall":  ("тиск ГУ — циліндр. стінка",  "Па"),
    "gu_pressure_west_gap":  ("тиск ГУ — західний зазор",   "Па"),
    "gu_pressure_east_gap":  ("тиск ГУ — східний зазор",    "Па"),
    "gu_pressure_vsro":      ("тиск ГУ — ВСРО",             "Па"),
    "gu_sigma_008":          ("СКО тиску 008p",             "Па"),
    "gu_sigma_009":          ("СКО тиску 009p",             "Па"),
    "gu_sigma_kp_os":        ("СКО тиску КП-ОС",            "Па"),
}


def _describe_issues(v: dict, scores: dict, top_n: int = 5) -> list[str]:
    """Return human-readable text for the top-N most-problematic channels.

    Generalised over CHANNEL_WEIGHTS instead of hardcoding per-channel
    branches — every channel that has a non-zero score contributes a
    description with its current value and warn band, and the worst
    offenders bubble up first.
    """
    ranked = sorted(
        ((k, s) for k, s in scores.items() if s > 0.01),
        key=lambda kv: kv[1],
        reverse=True,
    )[:top_n]

    out: list[str] = []
    for k, _score in ranked:
        label, unit = CHANNEL_LABELS.get(k, (k, ""))
        warn_lo, warn_hi, *_ = THRESHOLDS.get(k, (None, None, None, None))
        value = v.get(k)
        if value is None:
            continue
        if warn_lo is not None and warn_hi is not None:
            out.append(
                f"{label} {value:.2f} {unit} (норма {warn_lo:.1f}…{warn_hi:.1f} {unit})"
            )
        else:
            out.append(f"{label} {value:.2f} {unit}")
    return out


# ===== Stats =====
@app.get("/analytic/stats", response_model=list[StatsOut])
async def stats(hours: int = 24, _: dict = Depends(auth_required)):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """SELECT s.sensor_type,
                      COUNT(*)              AS count,
                      AVG(r.value)::float8  AS mean,
                      MIN(r.value)::float8  AS min,
                      MAX(r.value)::float8  AS max,
                      percentile_cont(0.95) WITHIN GROUP (ORDER BY r.value)::float8 AS p95
               FROM sensors.readings r
               JOIN sensors.sensors s ON s.id = r.sensor_id
               WHERE r.measured_at >= now() - ($1 || ' hours')::interval
               GROUP BY s.sensor_type
               ORDER BY s.sensor_type""",
            str(hours),
        )
    return [dict(r) for r in rows]


@app.get("/analytic/trend")
async def trend(
    sensor_type: str,
    hours: int = 24,
    bucket_minutes: int = 15,
    _: dict = Depends(auth_required),
):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """SELECT date_trunc('minute', r.measured_at)
                       - make_interval(mins => MOD(EXTRACT(MINUTE FROM r.measured_at)::int, $3)) AS bucket,
                     AVG(r.value)::float8 AS value
               FROM sensors.readings r
               JOIN sensors.sensors s ON s.id = r.sensor_id
               WHERE s.sensor_type = $1
                 AND r.measured_at >= now() - ($2 || ' hours')::interval
               GROUP BY bucket
               ORDER BY bucket""",
            sensor_type, str(hours), bucket_minutes,
        )
    return [{"t": r["bucket"].isoformat(), "value": r["value"]} for r in rows]


# ===== Optimization =====
@app.post("/analytic/optimize", response_model=OptimizationResult)
async def optimize(req: OptimizationIn, claims: dict = Depends(auth_required)):
    if req.flow_kp_max <= req.flow_kp_min:
        raise HTTPException(400, "flow_kp_max має бути більшим за flow_kp_min")
    if req.flow_oo_max <= req.flow_oo_min:
        raise HTTPException(400, "flow_oo_max має бути більшим за flow_oo_min")

    if req.method == "grid":
        result = _optimize_grid(req)
    else:
        result = _optimize_scipy(req)

    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO analytic.optimization_runs
                   (user_id, method, inputs, result, status, finished_at)
               VALUES ($1,$2,$3::jsonb,$4::jsonb,$5,$6)
               RETURNING id""",
            int(claims["sub"]) if claims.get("sub") else None,
            req.method,
            json.dumps(req.model_dump()),
            json.dumps(result),
            result["status"],
            datetime.now(timezone.utc),
        )
    result["id"] = row["id"]
    return result


@app.get("/analytic/runs")
async def list_runs(limit: int = 50, _: dict = Depends(auth_required)):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, method, inputs, result, status, created_at, finished_at
               FROM analytic.optimization_runs
               ORDER BY created_at DESC
               LIMIT $1""",
            limit,
        )
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "method": r["method"],
            "inputs": json.loads(r["inputs"]) if isinstance(r["inputs"], str) else r["inputs"],
            "result": json.loads(r["result"]) if isinstance(r["result"], str) else r["result"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
        })
    return out


# ===== Optimization core =====
# A simple physical surrogate model fitted to the dataset:
#   pressure_kp ≈ -100 * (flow_kp / max_flow_kp) * load + wind_offset
#   pressure_oo ≈ -110 * (flow_oo / max_flow_oo) * load + wind_offset
# (load = вентиляторне завантаження 0.05..1.0)
def _model(flow_kp: float, flow_oo: float, fan_load: float, req: OptimizationIn) -> dict:
    wind_off = 0.5 * (req.current_wind_speed - 2.0)
    norm_kp = flow_kp / max(req.flow_kp_max, 1.0)
    norm_oo = flow_oo / max(req.flow_oo_max, 1.0)
    pressure_kp = -100.0 * norm_kp * fan_load + wind_off + 5.0
    pressure_oo = -110.0 * norm_oo * fan_load + wind_off + 3.0
    dp_kp_oo = pressure_kp - pressure_oo
    energy = req.fan_power_kw * (fan_load ** 2 + 0.1) * (1.0 + 0.5 * (norm_kp + norm_oo))
    return {
        "pressure_kp": pressure_kp,
        "pressure_oo": pressure_oo,
        "dp_kp_oo":    dp_kp_oo,
        "energy":      energy,
    }


def _cost(flow_kp: float, flow_oo: float, fan_load: float, req: OptimizationIn) -> float:
    m = _model(flow_kp, flow_oo, fan_load, req)
    energy_cost = m["energy"] * req.energy_cost_kwh

    pkp_pen = (m["pressure_kp"] - req.pressure_kp_target) ** 2 * 1e-2
    poo_pen = (m["pressure_oo"] - req.pressure_oo_target) ** 2 * 1e-2

    # Penalize a too-low / negative dp_kp_oo strongly — it is the safety
    # margin that keeps contamination from drifting the wrong way
    dp_pen = 0.0
    if m["dp_kp_oo"] < req.dp_kp_oo_min:
        dp_pen = (req.dp_kp_oo_min - m["dp_kp_oo"]) ** 2 * 50.0

    fkp_pen = 0.0
    if flow_kp < req.flow_kp_min:
        fkp_pen += (req.flow_kp_min - flow_kp) ** 2 * 5.0
    if flow_kp > req.flow_kp_max:
        fkp_pen += (flow_kp - req.flow_kp_max) ** 2 * 5.0

    foo_pen = 0.0
    if flow_oo < req.flow_oo_min:
        foo_pen += (req.flow_oo_min - flow_oo) ** 2 * 5.0
    if flow_oo > req.flow_oo_max:
        foo_pen += (flow_oo - req.flow_oo_max) ** 2 * 5.0

    return energy_cost + pkp_pen + poo_pen + dp_pen + fkp_pen + foo_pen


def _build_result(flow_kp: float, flow_oo: float, fan_load: float,
                  req: OptimizationIn, status: str, iterations: int) -> dict:
    m = _model(flow_kp, flow_oo, fan_load, req)
    cost = m["energy"] * req.energy_cost_kwh
    margin = m["dp_kp_oo"] - req.dp_kp_oo_min
    return {
        "method": req.method,
        "optimal_flow_kp":  float(round(flow_kp, 3)),
        "optimal_flow_oo":  float(round(flow_oo, 3)),
        "optimal_fan_load": float(round(fan_load, 4)),
        "expected_pressure_kp": float(round(m["pressure_kp"], 2)),
        "expected_pressure_oo": float(round(m["pressure_oo"], 2)),
        "expected_dp_kp_oo":    float(round(m["dp_kp_oo"], 2)),
        "energy_kw":            float(round(m["energy"], 3)),
        "energy_cost_per_hour": float(round(cost, 3)),
        "safety_margin":        float(round(margin, 3)),
        "status": status,
        "iterations": int(iterations),
    }


def _optimize_scipy(req: OptimizationIn) -> dict:
    x0 = np.array([
        (req.flow_kp_min + req.flow_kp_max) / 2.0,
        (req.flow_oo_min + req.flow_oo_max) / 2.0,
        0.5,
    ])
    bounds = [
        (req.flow_kp_min, req.flow_kp_max),
        (req.flow_oo_min, req.flow_oo_max),
        (0.05, 1.0),
    ]
    res = minimize(
        lambda x: _cost(float(x[0]), float(x[1]), float(x[2]), req),
        x0=x0, bounds=bounds, method="L-BFGS-B",
    )
    fk, fo, fl = float(res.x[0]), float(res.x[1]), float(res.x[2])
    status = "ok" if res.success else "partial"
    return _build_result(fk, fo, fl, req, status, int(res.nit))


def _optimize_grid(req: OptimizationIn) -> dict:
    best = None
    iterations = 0
    for fk in np.linspace(req.flow_kp_min, req.flow_kp_max, 12):
        for fo in np.linspace(req.flow_oo_min, req.flow_oo_max, 12):
            for fl in np.linspace(0.05, 1.0, 12):
                iterations += 1
                c = _cost(float(fk), float(fo), float(fl), req)
                if best is None or c < best[0]:
                    best = (c, float(fk), float(fo), float(fl))
    assert best is not None
    return _build_result(best[1], best[2], best[3], req, "ok", iterations)
