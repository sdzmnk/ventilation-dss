# Ventilation DSS

Decision Support System for ventilation control in nuclear / hazardous facilities.
Microservice architecture written in Python (FastAPI) with a React/Vite frontend,
single PostgreSQL instance with one schema per service, and a gateway that fronts
HTTP and WebSocket traffic for the browser.

## Services

| Service             | Port  | Schema           | Responsibility                                                                 |
| ------------------- | ----- | ---------------- | ------------------------------------------------------------------------------ |
| `auth-service`      | 8001  | `auth`           | Registration, login, JWT issuance / refresh / verify                          |
| `user-service`      | 8002  | `profile`        | Per-user profile CRUD, admin user management                                   |
| `data-service`      | 8003  | `sensors`        | Zones, sensors, readings; replays real 2020-2024 dataset (`db/ventilation_history.csv`) |
| `analytic-service`  | 8004  | `analytic`       | Aggregated stats, trends, ventilation optimization (`scipy` / grid search)    |
| `config-service`    | 8005  | `configuration`  | Runtime parameters (limits, costs, efficiency)                                |
| `discovery-service` | 8006  | `discovery`      | Registry of services + periodic `/health` probing                              |
| `chat-service`      | 8007  | `chat`           | Rooms, history, REST send + WebSocket broadcast                                |
| `gateway-service`   | 8000  | —                | Reverse proxy / API gateway, including chat WebSocket relay                    |
| `frontend`          | 5173  | —                | React + Vite SPA served by Nginx, proxies `/api` to the gateway                |
| `postgres`          | 5432  | —                | Shared database (one schema per service)                                       |

## Quick start

```bash
cp .env.example .env       # adjust JWT_SECRET in production
docker compose up --build
```

Then open <http://localhost:5173>.

The seeded admin account is:

- username: `admin`
- password: `admin123`

### Sensor data

The system runs on **real measurement data from a hermetic ventilation
zone (КП / ОО / гермоустановка), aggregated from 2020–2024**. The raw
Excel exports (`output_sum 2020 (1).xlsx` … `output_sum 2024.xlsx`) are
preprocessed by `build_dataset.py` into:

- `db/ventilation_history.csv`     — ~2500 normalized snapshots covering
  24 sensor channels (wind, КП/ОО pressures, КП+/ОО± flows, ΔP variants,
  ГУ wall pressures, σ pressures);
- `db/ventilation_baselines.json`  — per-channel mean/std/p05/p50/p95.

`docker-compose` mounts both files into the `data-service` and
`analytic-service` containers. On startup, `data-service` seeds the
readings table from the CSV (re-basing timestamps to "now") and then
walks through the file row-by-row, replaying real readings as live data.
`analytic-service` uses the baseline statistics to calibrate the
prediction thresholds.

To regenerate the dataset from the source spreadsheets, run:

```bash
pip install pandas openpyxl
python build_dataset.py
```

End users see only the operational surfaces — overview, sensors,
optimization, parameters, comms, profile. Administrators additionally
see **Користувачі** and **Ролі** for managing accounts and access levels.

## Endpoints (via gateway, base `http://localhost:8000`)

- `POST /auth/register` (always creates an `operator`), `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`, `GET /auth/verify?token=...`
- `GET/PUT /users/me`, `GET /users` (admin), `GET/PUT/DELETE /users/{id}`, `PATCH /users/{id}/role` (admin only)
- `GET/POST /zones`, `GET/POST /sensors`, `GET/POST /readings`, `GET /readings/latest`, `POST /simulate`
- `GET /analytic/stats`, `GET /analytic/trend?sensor_type=...`, `POST /analytic/optimize`, `GET /analytic/runs`
- `GET /config`, `GET/PUT/DELETE /config/{key}`
- `GET /registry`, `POST /registry`, `DELETE /registry/{name}`
- `GET /chat/rooms`, `POST /chat/rooms`, `GET /chat/rooms/{id}/messages`, `POST /chat/rooms/{id}/messages`
- `WS /chat/ws/{room_id}?token=...`
- `GET /services` — gateway probe of every backend
- `GET /health` — on every service

## Roles

Registration always creates an `operator`. Roles can only be elevated by an
admin from the **Ролі** tab (or via `PATCH /users/{id}/role`).

- `admin` — full access (manage users, sensor topology, configuration, role assignment)
- `engineer` — manage sensors and run optimization
- `operator` — read-only dashboard, run optimization, comms

## Architecture notes

- **Authentication** is centralized in `auth-service`. Every other service
  validates the same JWT locally with `JWT_SECRET` (no extra round-trip).
- **Gateway** matches the request prefix against a route table and forwards to
  the corresponding service over the docker network. The same gateway also
  proxies the WebSocket connection used by the chat UI.
- **Discovery** continuously polls `/health` on every registered service every
  15 seconds and stores the result in `discovery.services`.
- **Optimization** in `analytic-service` minimizes the cost
  `energy + Σ pressure_penalties + dp_kp_oo_penalty + flow_penalties`
  over three control variables (`flow_kp`, `flow_oo`, `fan_load`) using
  SciPy's L-BFGS-B or a grid search, then persists each run.
- **Prediction** classifies the 9 safety-critical channels (КП/ОО pressure,
  ΔP КП-ОО, КП+/ОО− flows, wind, three ГУ wall pressures) against
  thresholds calibrated from the 2020-2024 dataset.

## Project layout

```
.
├── build_dataset.py              # Excel → CSV + baselines preprocessor
├── db/
│   ├── init.sql                  # schemas + zone/sensor topology
│   ├── ventilation_history.csv   # 2020-2024 real readings (replayed by data-service)
│   └── ventilation_baselines.json
├── docker-compose.yml
├── frontend/                  # React + Vite + Nginx
│   ├── src/
│   │   ├── api/               # axios client + auth context
│   │   ├── components/        # shared UI (charts, ...)
│   │   ├── i18n/              # uk / en dictionaries
│   │   └── pages/             # Login, Dashboard, Sensors, Optimization, ...
│   ├── Dockerfile
│   └── nginx.conf
└── services/
    ├── auth-service/
    ├── user-service/
    ├── data-service/
    ├── analytic-service/
    ├── config-service/
    ├── discovery-service/
    ├── chat-service/
    └── gateway-service/
```
