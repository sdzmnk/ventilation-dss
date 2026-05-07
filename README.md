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
| `data-service`      | 8003  | `sensors`        | Zones, sensors, readings; synthetic data generator                            |
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

Sensor data is ingested automatically in the background, so the dashboard
always shows live readings without any manual action. End users see only the
operational surfaces — overview, sensors, optimization, parameters, comms,
profile. Administrators additionally see **Користувачі** and **Ролі** for
managing accounts and access levels.

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
  `energy + radiation_penalty + pressure_penalty + airflow_penalty` either with
  SciPy's L-BFGS-B or via a grid search, then persists each run.

## Project layout

```
.
├── db/init.sql                # schemas + seed data
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
