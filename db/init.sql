-- Schemas per service
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS profile;
CREATE SCHEMA IF NOT EXISTS sensors;
CREATE SCHEMA IF NOT EXISTS analytic;
CREATE SCHEMA IF NOT EXISTS configuration;
CREATE SCHEMA IF NOT EXISTS discovery;
CREATE SCHEMA IF NOT EXISTS chat;

-- ===== auth =====
CREATE TABLE IF NOT EXISTS auth.users (
    id           BIGSERIAL PRIMARY KEY,
    username     VARCHAR(64) UNIQUE NOT NULL,
    email        VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role         VARCHAR(32) NOT NULL DEFAULT 'operator',
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auth.refresh_tokens (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token        TEXT NOT NULL,
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- seed admin (password: admin123, bcrypt of "admin123")
INSERT INTO auth.users (username, email, password_hash, role)
VALUES ('admin', 'admin@vent.local',
        '$2b$12$rRG7dLG7rAd3sV0FQg5pIuxvbxV.zP1Fo0ZD16qPDvLpXg06o.Sni',
        'admin')
ON CONFLICT DO NOTHING;

-- ===== profile (user-service) =====
CREATE TABLE IF NOT EXISTS profile.user_profiles (
    user_id     BIGINT PRIMARY KEY,
    full_name   VARCHAR(255),
    position    VARCHAR(128),
    department  VARCHAR(128),
    phone       VARCHAR(64),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== sensors (data-service) =====
CREATE TABLE IF NOT EXISTS sensors.zones (
    id          BIGSERIAL PRIMARY KEY,
    code        VARCHAR(32) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS sensors.sensors (
    id          BIGSERIAL PRIMARY KEY,
    zone_id     BIGINT REFERENCES sensors.zones(id) ON DELETE CASCADE,
    code        VARCHAR(64) UNIQUE NOT NULL,
    sensor_type VARCHAR(32) NOT NULL,
    unit        VARCHAR(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS sensors.readings (
    id          BIGSERIAL PRIMARY KEY,
    sensor_id   BIGINT NOT NULL REFERENCES sensors.sensors(id) ON DELETE CASCADE,
    value       DOUBLE PRECISION NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_readings_sensor_time ON sensors.readings(sensor_id, measured_at DESC);

-- seed zones / sensors
INSERT INTO sensors.zones (code, name, description) VALUES
    ('Z-01', 'Реакторний зал', 'Основна зона радіаційного контролю'),
    ('Z-02', 'Машинний зал', 'Машинне обладнання'),
    ('Z-03', 'Сховище ВЯП', 'Сховище відпрацьованого ядерного палива')
ON CONFLICT DO NOTHING;

INSERT INTO sensors.sensors (zone_id, code, sensor_type, unit) VALUES
    (1, 'R-01-RAD', 'radiation', 'мкЗв/год'),
    (1, 'R-01-PRES', 'pressure', 'Па'),
    (1, 'R-01-FLOW', 'airflow', 'м³/год'),
    (1, 'R-01-TEMP', 'temperature', '°C'),
    (2, 'M-02-RAD', 'radiation', 'мкЗв/год'),
    (2, 'M-02-PRES', 'pressure', 'Па'),
    (2, 'M-02-FLOW', 'airflow', 'м³/год'),
    (3, 'S-03-RAD', 'radiation', 'мкЗв/год'),
    (3, 'S-03-PRES', 'pressure', 'Па'),
    (3, 'S-03-FLOW', 'airflow', 'м³/год')
ON CONFLICT DO NOTHING;

-- ===== analytic =====
CREATE TABLE IF NOT EXISTS analytic.optimization_runs (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT,
    method      VARCHAR(32) NOT NULL,
    inputs      JSONB NOT NULL,
    result      JSONB,
    status      VARCHAR(16) NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

-- ===== configuration =====
CREATE TABLE IF NOT EXISTS configuration.parameters (
    id          BIGSERIAL PRIMARY KEY,
    key         VARCHAR(128) UNIQUE NOT NULL,
    value       JSONB NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO configuration.parameters (key, value, description) VALUES
    ('radiation_limit_uSv', '20.0', 'Гранична потужність дози (мкЗв/год)'),
    ('pressure_min_pa', '-50.0', 'Мінімальний перепад тиску, Па'),
    ('pressure_max_pa', '-200.0', 'Максимальний перепад тиску, Па'),
    ('airflow_min_m3h', '5000', 'Мінімальна витрата повітря, м³/год'),
    ('airflow_max_m3h', '40000', 'Максимальна витрата повітря, м³/год'),
    ('energy_cost_kwh', '0.12', 'Вартість 1 кВт·год'),
    ('fan_power_kw', '15.0', 'Потужність вентилятора, кВт'),
    ('filter_efficiency', '0.999', 'Ефективність HEPA фільтру')
ON CONFLICT DO NOTHING;

-- ===== discovery =====
CREATE TABLE IF NOT EXISTS discovery.services (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(64) UNIQUE NOT NULL,
    url         VARCHAR(255) NOT NULL,
    healthy     BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== chat =====
CREATE TABLE IF NOT EXISTS chat.rooms (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(128),
    is_dm       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rooms_name ON chat.rooms(name) WHERE is_dm = FALSE;

INSERT INTO chat.rooms (name, is_dm) VALUES ('general', FALSE), ('alerts', FALSE) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS chat.dm_participants (
    room_id     BIGINT NOT NULL REFERENCES chat.rooms(id) ON DELETE CASCADE,
    user_id     BIGINT NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    PRIMARY KEY (room_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_dm_user ON chat.dm_participants(user_id);

CREATE TABLE IF NOT EXISTS chat.messages (
    id          BIGSERIAL PRIMARY KEY,
    room_id     BIGINT NOT NULL REFERENCES chat.rooms(id) ON DELETE CASCADE,
    user_id     BIGINT,
    username    VARCHAR(64),
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_msg_room ON chat.messages(room_id, created_at DESC);
