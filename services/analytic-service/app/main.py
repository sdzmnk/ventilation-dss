"""Analytic service — XGBoost-based ventilation state classifier.

The /analytic/predict endpoint is now backed by an XGBoost model trained
on the 2020-2024 ventilation history (22 monitored channels). Labels are
generated from the legacy rule-based composite danger score, so the
trained model reproduces existing operational policy while learning the
mapping directly from raw sensor readings.

  * pressure_kp            — тиск у герметичній зоні (КП)
  * pressure_oo            — тиск у приміщенні ОО
  * dp_kp_oo               — перепад КП-ОО (повинен бути позитивним)
  * flow_kp_in             — витрата КП+ (приплив у КП)
  * flow_oo_out            — витрата ОО- (витяжка ОО)
  * wind_speed             — зовнішній вітер (вплив на герметичність)
  * gu_pressure_*          — тиски на стінках гермоустановки
  * gu_sigma_*             — СКО тиску, прокси-показник турбулентності

Baselines: /data/ventilation_baselines.json (mounted from db/).
Training set: /data/ventilation_history.csv (mounted from db/).
"""
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import jwt
import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(__file__))

from ml.data_preprocess import VentilationPreprocessingService
from ml.hvac_service import HVACVentilationModelService
from ml.recommender import Recommender
from ml.weight_service import WeightService

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
BASELINES_JSON = os.getenv("VENT_BASELINES_JSON", "/data/ventilation_baselines.json")
DATASET_CSV = os.getenv("VENT_DATASET_CSV", "/data/ventilation_history.csv")

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
model_service: Optional[HVACVentilationModelService] = None
recommender: Optional[Recommender] = None


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


@app.on_event("startup")
async def _startup() -> None:
    _load_baselines()
    _train_model()
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


def _train_model() -> None:
    global model_service, recommender
    model_service = HVACVentilationModelService(baselines=_BASELINES)
    recommender = Recommender()

    if not os.path.exists(DATASET_CSV):
        print(f"[analytic-service] dataset CSV not found at {DATASET_CSV} — models untrained")
        return

    raw = pd.read_csv(DATASET_CSV)
    clean = VentilationPreprocessingService.preprocess(raw)
    print(f"[analytic-service] training XGBoost on {len(clean)} rows × {len(clean.columns)} cols")
    model_service.train(clean)

    if model_service.is_trained:
        acc = model_service.metrics.get("accuracy")
        print(f"[analytic-service] XGBoost ready: accuracy={acc} classes={list(model_service.encoder.classes_)}")
    print(f"[analytic-service] Recommender LLM {'enabled' if recommender.enabled else 'disabled (using data-driven fallback)'}")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "analytic-service",
        "xgboost_trained": bool(model_service and model_service.is_trained),
        "recommender_enabled": bool(recommender and recommender.enabled),
    }


@app.get("/analytic/model-metrics")
async def model_metrics(_: dict = Depends(auth_required)):
    if not model_service or not model_service.is_trained:
        raise HTTPException(503, "Модель ще не натренована")
    return model_service.metrics


KNOWN_CHANNELS = WeightService.known_channels()
WEIGHTED_CHANNELS = list(WeightService.CHANNEL_WEIGHTS.keys())


@app.get("/analytic/predict")
async def predict(
    request: Request,
    hours: int = Query(24, ge=1, le=720),
    _: dict = Depends(auth_required),
):
    """Classify ventilation system state via the trained XGBoost model.

    Accepts every weighted channel as an optional query parameter
    (e.g. `?pressure_kp=-12&dp_kp_oo=8&gu_sigma_008=0.5`). Channels not
    provided are filled from the average of the last `hours` readings,
    then from the dataset median, then from the nominal threshold midpoint.
    """
    if not model_service or not model_service.is_trained:
        raise HTTPException(503, "Модель ще не натренована")

    given: dict[str, float] = {}
    missing: list[str] = []
    for k in WEIGHTED_CHANNELS:
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
                t = model_service.feature_engineer.score_service.thresholds.get(k)
                given[k] = (t[0] + t[1]) / 2.0 if t else 0.0

    ml_out = model_service.predict(given)

    probabilities = {
        cls: ml_out["probabilities"].get(cls, 0.0)
        for cls in ("OK", "WARNING", "CRITICAL")
    }
    prediction_data = {
        "status": ml_out["status"],
        "risk_score": ml_out["risk_score"],
        "confidence": ml_out["confidence"],
        "probabilities": {k: round(float(v), 4) for k, v in probabilities.items()},
        "top_channels": model_service.top_channels[:5],
    }
    return {
        "prediction_data": prediction_data,
        "inputs": {k: round(float(v), 3) for k, v in given.items()},
        "recommendation": _build_recommendation(prediction_data, given),
    }


def _build_recommendation(prediction_data: dict, inputs: dict) -> str:
    """Рекомендація формується LLM-ом (Recommender) на основі XGBoost output.
    Якщо LLM не сконфігуровано — повертаємо стислий data-driven текст
    із топ-каналів моделі та їхніх поточних значень.
    """
    drivers = _describe_top_features(inputs, top_n=5)

    if recommender and recommender.enabled:
        payload = {**prediction_data, "key_channels": drivers}
        try:
            advice = recommender.generate_advice(payload)
            if advice and advice.strip():
                return advice.strip()
        except Exception as exc:
            print(f"[analytic-service] Recommender failed, using fallback: {exc}")

    return _fallback_recommendation(prediction_data, drivers)


def _fallback_recommendation(prediction_data: dict, drivers: list[str]) -> str:
    status = prediction_data["status"]
    confidence = prediction_data.get("confidence") or 0.0
    risk = prediction_data.get("risk_score")
    conf_pct = f"{confidence * 100:.1f}%"
    drivers_text = "; ".join(drivers) if drivers else "немає даних про важливі канали"
    status_uk = {"OK": "у нормі", "WARNING": "відхилення", "CRITICAL": "критичний стан"}.get(status, status)
    risk_text = f", індекс безпеки {risk}" if risk is not None else ""
    return (
        f"Стан системи: {status_uk} (впевненість {conf_pct}{risk_text}).\n"
        f"Ключові канали моделі: {drivers_text}.\n"
        f"Рекомендовано звірити перелічені канали з робочими діапазонами та зафіксувати показання."
    )


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


def _describe_top_features(v: dict, top_n: int = 5) -> list[str]:
    """Top-N raw channels by XGBoost feature_importance + their current values."""
    if not model_service or not model_service.is_trained:
        return []
    out: list[str] = []
    for k in model_service.top_channels[:top_n]:
        value = v.get(k)
        if value is None:
            continue
        label, unit = CHANNEL_LABELS.get(k, (k, ""))
        out.append(f"{label} {value:.2f} {unit}".rstrip())
    return out


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
