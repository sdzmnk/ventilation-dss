import json
import math
import os
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import jwt
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from scipy.optimize import minimize

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

app = FastAPI(title="Analytic Service")
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
    radiation_limit: float = Field(20.0, gt=0, description="мкЗв/год")
    pressure_target: float = Field(-120.0, description="Па")
    airflow_min: float = Field(5000.0, gt=0)
    airflow_max: float = Field(40000.0, gt=0)
    filter_efficiency: float = Field(0.999, gt=0, le=1)
    current_radiation: float = Field(10.0, ge=0)


class OptimizationResult(BaseModel):
    id: Optional[int] = None
    method: str
    optimal_airflow: float
    optimal_fan_load: float
    expected_radiation: float
    expected_pressure: float
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
    await get_pool()


@app.on_event("shutdown")
async def _shutdown() -> None:
    if pool:
        await pool.close()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "analytic-service"}


# ===== Predict =====
@app.get("/analytic/predict")
async def predict(
    radiation:   Optional[float] = Query(None),
    pressure:    Optional[float] = Query(None),
    airflow:     Optional[float] = Query(None),
    temperature: Optional[float] = Query(None),
    hours:       int             = Query(24, ge=1, le=720),
    _: dict = Depends(auth_required),
):
    """Classify ventilation system state.

    If radiation/pressure/airflow/temperature are provided the endpoint uses
    those values directly (so the frontend can pass exactly what it already
    displays).  Otherwise it falls back to the average over `hours` hours from
    the database — the same aggregation used by /analytic/stats.
    """
    need_db = any(v is None for v in (radiation, pressure, airflow, temperature))
    if need_db:
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
        radiation   = radiation   if radiation   is not None else db.get("radiation",    8.0)
        pressure    = pressure    if pressure    is not None else db.get("pressure",  -120.0)
        airflow     = airflow     if airflow     is not None else db.get("airflow",  18000.0)
        temperature = temperature if temperature is not None else db.get("temperature",  22.0)

    # Danger score per parameter [0, 1]; calibrated so baseline readings → ~0.01
    rad_score = (
        1.0 if radiation >= 20.0
        else 0.5 + 0.5 * (radiation - 16.0) / 4.0 if radiation >= 16.0
        else (radiation / 16.0) * 0.035
    )
    pres_score = (
        0.0 if -180.0 <= pressure <= -60.0
        else min(1.0, abs(pressure + 120.0) / 120.0)
    )
    flow_score = (
        min(1.0, (5000.0 - airflow) / 5000.0) if airflow < 5000.0
        else min(1.0, (airflow - 40000.0) / 10000.0) if airflow > 40000.0
        else 0.0
    )
    temp_score = (
        min(1.0, (temperature - 28.0) / 12.0) if temperature > 28.0
        else 0.0
    )

    composite = min(1.0, (
        rad_score  * 0.5 +
        pres_score * 0.2 +
        flow_score * 0.2 +
        temp_score * 0.1
    ))

    # Probabilities — always sum to 1; symmetric WARNING/CRITICAL in safe regime
    if composite < 0.35:
        p_ok       = 1.0 - composite
        p_warning  = composite / 2.0
        p_critical = composite / 2.0
        status = "OK"
    elif composite < 0.65:
        t          = (composite - 0.35) / 0.30
        p_ok       = 1.0 - composite
        p_warning  = composite * (0.5 + 0.5 * t)
        p_critical = composite * (0.5 - 0.5 * t)
        status = "WARNING" if p_warning > p_ok else "OK"
    else:
        t          = (composite - 0.65) / 0.35
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
        },
        "recommendation": _build_recommendation(
            status, confidence, radiation, pressure, airflow, temperature
        ),
    }


def _build_recommendation(
    status: str,
    confidence: float,
    radiation: float,
    pressure: float,
    airflow: float,
    temperature: float,
) -> str:
    conf_pct = f"{confidence * 100:.2f}%"

    if status == "OK":
        causes = []
        if radiation > 12.0:
            causes.append("незначне підвищення рівня радіації, що наближається до порогу попередження")
        if not (-160.0 <= pressure <= -80.0):
            causes.append("невеликі відхилення тиску від оптимального діапазону")
        if airflow < 8000.0 or airflow > 35000.0:
            causes.append("незначні коливання витрати повітря через вплив зовнішніх факторів")
        cause_str = (
            "; ".join(causes)
            if causes
            else "незначне забруднення фільтрів або коливання витрати повітря через зовнішні чинники"
        )
        return (
            f"Вентиляційна система працює в межах норми з рівнем впевненості {conf_pct}. "
            f"Індекс безпеки свідчить про відсутність безпосередніх загроз для експлуатації. "
            f"Проте існує невелика ймовірність розвитку відхилень з часом. "
            f"Можливі причини: {cause_str}. "
            "Ці умови можуть призвести до перегріву обладнання, якщо їх не усунути своєчасно.\n\n"
            "Рекомендація оператору: здійснювати регулярний моніторинг системи на наявність "
            "сторонніх шумів, незвичних запахів або стрибків температури. "
            "У разі збереження симптомів — провести очищення фільтрів або скоригувати "
            "налаштування вентилятора для забезпечення оптимальної продуктивності."
        )

    if status == "WARNING":
        issues = []
        if radiation >= 16.0:
            issues.append(f"рівень радіації {radiation:.1f} мкЗв/год наближається до критичної межі 20,0 мкЗв/год")
        if not (-180.0 <= pressure <= -60.0):
            issues.append(f"тиск {pressure:.1f} Па виходить за межі безпечного діапазону")
        if airflow < 5000.0:
            issues.append(f"витрата повітря {airflow:.0f} м³/год нижча за мінімальний поріг 5000 м³/год")
        if temperature > 28.0:
            issues.append(f"температура {temperature:.1f} °C перевищує норму")
        issue_text = "; ".join(issues) if issues else "відхилення кількох параметрів від оптимальних значень"
        return (
            f"Вентиляційна система демонструє ознаки відхилення з рівнем впевненості {conf_pct}. "
            f"Виявлені проблеми: {issue_text}.\n\n"
            "Необхідні дії: збільшити частоту перевірок до одного разу на 2 години. "
            "Перевірити стан фільтрів і замінити їх, якщо перепад тиску на фільтрах перевищує 50 Па. "
            "Перевірити роботу вентилятора та скоригувати швидкість, якщо відхилення витрати зберігаються. "
            "Повідомити інженерну службу та підготувати резервний план дій."
        )

    # CRITICAL
    critical_issues = []
    if radiation >= 20.0:
        critical_issues.append(f"радіація {radiation:.1f} мкЗв/год ПЕРЕВИЩУЄ безпечну межу 20,0 мкЗв/год")
    if pressure < -180.0 or pressure > -60.0:
        critical_issues.append(f"тиск {pressure:.1f} Па — критичне відхилення від норми")
    if airflow < 5000.0:
        critical_issues.append(f"витрата повітря {airflow:.0f} м³/год — критично низька")
    if temperature > 35.0:
        critical_issues.append(f"температура {temperature:.1f} °C перевищує критичний поріг")
    issue_text = "; ".join(critical_issues) if critical_issues else "виявлено критичні порушення параметрів"
    return (
        f"КРИТИЧНА СИТУАЦІЯ: вентиляційна система потребує негайного втручання. "
        f"Рівень впевненості: {conf_pct}. "
        f"Критичні порушення: {issue_text}.\n\n"
        "Аварійне реагування: негайно активувати аварійний режим вентиляції. "
        "Евакуювати персонал із уражених зон, якщо радіація перевищує допустимі норми опромінення. "
        "Повідомити відповідального з охорони праці та ініціювати аварійне відключення, якщо "
        "параметри не повернуться до безпечних значень протягом 15 хвилин. "
        "Відновлення роботи в штатному режимі дозволяється лише після усунення всіх критичних "
        "відхилень та підтвердження інженерною службою."
    )


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
    if req.airflow_max <= req.airflow_min:
        raise HTTPException(400, "airflow_max має бути більшим за airflow_min")

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
def _model(airflow: float, fan_load: float, req: OptimizationIn) -> dict:
    """Return predicted radiation, pressure and energy for given operating point."""
    norm = airflow / max(req.airflow_max, 1.0)
    radiation = req.current_radiation * (1.0 - req.filter_efficiency * min(1.0, norm))
    pressure = -50.0 - 200.0 * fan_load
    energy = req.fan_power_kw * (fan_load ** 2 + 0.1)
    return {"radiation": radiation, "pressure": pressure, "energy": energy}


def _cost(airflow: float, fan_load: float, req: OptimizationIn) -> float:
    m = _model(airflow, fan_load, req)
    energy_cost = m["energy"] * req.energy_cost_kwh
    rad_pen = max(0.0, m["radiation"] - req.radiation_limit) ** 2 * 1e3
    pres_pen = (m["pressure"] - req.pressure_target) ** 2 * 1e-2
    flow_pen = 0.0
    if airflow < req.airflow_min:
        flow_pen += (req.airflow_min - airflow) ** 2 * 1e-3
    if airflow > req.airflow_max:
        flow_pen += (airflow - req.airflow_max) ** 2 * 1e-3
    return energy_cost + rad_pen + pres_pen + flow_pen


def _build_result(airflow: float, fan_load: float, req: OptimizationIn,
                  status: str, iterations: int) -> dict:
    m = _model(airflow, fan_load, req)
    cost = m["energy"] * req.energy_cost_kwh
    margin = req.radiation_limit - m["radiation"]
    return {
        "method": req.method,
        "optimal_airflow": float(round(airflow, 2)),
        "optimal_fan_load": float(round(fan_load, 4)),
        "expected_radiation": float(round(m["radiation"], 3)),
        "expected_pressure": float(round(m["pressure"], 2)),
        "energy_kw": float(round(m["energy"], 3)),
        "energy_cost_per_hour": float(round(cost, 3)),
        "safety_margin": float(round(margin, 3)),
        "status": status,
        "iterations": int(iterations),
    }


def _optimize_scipy(req: OptimizationIn) -> dict:
    x0 = np.array([(req.airflow_min + req.airflow_max) / 2.0, 0.5])
    bounds = [(req.airflow_min, req.airflow_max), (0.05, 1.0)]
    res = minimize(
        lambda x: _cost(float(x[0]), float(x[1]), req),
        x0=x0, bounds=bounds, method="L-BFGS-B",
    )
    af, fl = float(res.x[0]), float(res.x[1])
    status = "ok" if res.success else "partial"
    return _build_result(af, fl, req, status, int(res.nit))


def _optimize_grid(req: OptimizationIn) -> dict:
    best = None
    iterations = 0
    for af in np.linspace(req.airflow_min, req.airflow_max, 25):
        for fl in np.linspace(0.05, 1.0, 20):
            iterations += 1
            c = _cost(float(af), float(fl), req)
            if best is None or c < best[0]:
                best = (c, float(af), float(fl))
    assert best is not None
    return _build_result(best[1], best[2], req, "ok", iterations)
