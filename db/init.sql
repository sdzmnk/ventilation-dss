CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS profile;
CREATE SCHEMA IF NOT EXISTS sensors;
CREATE SCHEMA IF NOT EXISTS analytic;
CREATE SCHEMA IF NOT EXISTS configuration;
CREATE SCHEMA IF NOT EXISTS discovery;
CREATE SCHEMA IF NOT EXISTS chat;

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

INSERT INTO auth.users (username, email, password_hash, role)
VALUES ('admin', 'admin@vent.local',
        '$2b$12$rRG7dLG7rAd3sV0FQg5pIuxvbxV.zP1Fo0ZD16qPDvLpXg06o.Sni',
        'admin')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS profile.user_profiles (
    user_id     BIGINT PRIMARY KEY,
    full_name   VARCHAR(255),
    position    VARCHAR(128),
    department  VARCHAR(128),
    phone       VARCHAR(64),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
    sensor_type VARCHAR(64) NOT NULL,
    unit        VARCHAR(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS sensors.readings (
    id          BIGSERIAL PRIMARY KEY,
    sensor_id   BIGINT NOT NULL REFERENCES sensors.sensors(id) ON DELETE CASCADE,
    value       DOUBLE PRECISION NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_readings_sensor_time ON sensors.readings(sensor_id, measured_at DESC);

INSERT INTO sensors.zones (code, name, description) VALUES
    ('ENV',  'Зовнішнє середовище',          'Метеопараметри: вітер, густина повітря'),
    ('KP',   'Герметична зона (контайнмент)', 'Тиск і витрата у герметичній зоні'),
    ('OO',   'Приміщення обстеження-обслуговування', 'Тиск і витрати у зоні ОО'),
    ('DIFF', 'Перепади тисків',               'Перепади між зонами КП, ОО, ОС (різні точки виміру)'),
    ('GU',   'Гермоустановка',                'Тиски на стінках, зазорах та СКО')
ON CONFLICT DO NOTHING;

INSERT INTO sensors.sensors (zone_id, code, sensor_type, unit) VALUES
    ((SELECT id FROM sensors.zones WHERE code='ENV'),  'ENV-WSP',   'wind_speed',           'м/с'),
    ((SELECT id FROM sensors.zones WHERE code='ENV'),  'ENV-WDIR',  'wind_direction',       '°'),
    ((SELECT id FROM sensors.zones WHERE code='ENV'),  'ENV-RHO',   'air_density',          'кг/м³'),
    ((SELECT id FROM sensors.zones WHERE code='KP'),   'KP-PRES',   'pressure_kp',          'Па'),
    ((SELECT id FROM sensors.zones WHERE code='KP'),   'KP-FLOW-IN','flow_kp_in',           'тис. м³/год'),
    ((SELECT id FROM sensors.zones WHERE code='OO'),   'OO-PRES',   'pressure_oo',          'Па'),
    ((SELECT id FROM sensors.zones WHERE code='OO'),   'OO-FLOW-OUT','flow_oo_out',         'тис. м³/год'),
    ((SELECT id FROM sensors.zones WHERE code='OO'),   'OO-FLOW-IN','flow_oo_in',           'тис. м³/год'),
    ((SELECT id FROM sensors.zones WHERE code='DIFF'), 'DP-KP-OS',     'dp_kp_os',          'Па'),
    ((SELECT id FROM sensors.zones WHERE code='DIFF'), 'DP-OO-OS-8',   'dp_oo_os_8',        'Па'),
    ((SELECT id FROM sensors.zones WHERE code='DIFF'), 'DP-OO-OS-9',   'dp_oo_os_9',        'Па'),
    ((SELECT id FROM sensors.zones WHERE code='DIFF'), 'DP-KP-OO',     'dp_kp_oo',          'Па'),
    ((SELECT id FROM sensors.zones WHERE code='DIFF'), 'DP-KP-OO-BY',  'dp_kp_oo_by',       'Па'),
    ((SELECT id FROM sensors.zones WHERE code='DIFF'), 'DP-KP-OO-BZ',  'dp_kp_oo_bz',       'Па'),
    ((SELECT id FROM sensors.zones WHERE code='DIFF'), 'DP-KP-OO-CA',  'dp_kp_oo_ca',       'Па'),
    ((SELECT id FROM sensors.zones WHERE code='GU'),   'GU-P-W',     'gu_pressure_west_wall', 'Па'),
    ((SELECT id FROM sensors.zones WHERE code='GU'),   'GU-P-E',     'gu_pressure_east_wall', 'Па'),
    ((SELECT id FROM sensors.zones WHERE code='GU'),   'GU-P-CYL',   'gu_pressure_cyl_wall',  'Па'),
    ((SELECT id FROM sensors.zones WHERE code='GU'),   'GU-P-WGAP',  'gu_pressure_west_gap',  'Па'),
    ((SELECT id FROM sensors.zones WHERE code='GU'),   'GU-P-EGAP',  'gu_pressure_east_gap',  'Па'),
    ((SELECT id FROM sensors.zones WHERE code='GU'),   'GU-P-VSRO',  'gu_pressure_vsro',      'Па'),
    ((SELECT id FROM sensors.zones WHERE code='GU'),   'GU-S-008',   'gu_sigma_008',          'Па'),
    ((SELECT id FROM sensors.zones WHERE code='GU'),   'GU-S-009',   'gu_sigma_009',          'Па'),
    ((SELECT id FROM sensors.zones WHERE code='GU'),   'GU-S-KPOS',  'gu_sigma_kp_os',        'Па')
ON CONFLICT DO NOTHING;

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

CREATE TABLE IF NOT EXISTS configuration.parameters (
    id          BIGSERIAL PRIMARY KEY,
    key         VARCHAR(128) UNIQUE NOT NULL,
    value       JSONB NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO configuration.parameters (key, value, description) VALUES
    ('pressure_kp_min_pa',   '-50.0', 'Мінімальний тиск КП (Па) — нижче починається попередження'),
    ('pressure_kp_max_pa',    '15.0', 'Максимальний тиск КП (Па)'),
    ('pressure_oo_min_pa',   '-60.0', 'Мінімальний тиск ОО (Па)'),
    ('pressure_oo_max_pa',    '15.0', 'Максимальний тиск ОО (Па)'),
    ('dp_kp_oo_min_pa',      '-15.0', 'Мінімальний перепад КП-ОО (Па)'),
    ('dp_kp_oo_max_pa',       '20.0', 'Максимальний перепад КП-ОО (Па)'),
    ('flow_kp_min_km3h',      '10.0', 'Мінімальна витрата КП+ (тис. м³/год)'),
    ('flow_kp_max_km3h',      '28.0', 'Максимальна витрата КП+ (тис. м³/год)'),
    ('flow_oo_min_km3h',      '15.0', 'Мінімальна витрата ОО- (тис. м³/год)'),
    ('flow_oo_max_km3h',      '40.0', 'Максимальна витрата ОО- (тис. м³/год)'),
    ('wind_speed_alarm_ms',   '8.0',  'Порогова швидкість вітру для попередження (м/с)'),
    ('gu_pressure_alarm_pa', '40.0',  'Поріг |тиску| на стінках ГУ для попередження (Па)'),
    ('energy_cost_kwh',       '0.12', 'Вартість 1 кВт·год'),
    ('fan_power_kw',          '15.0', 'Потужність вентилятора, кВт'),
    ('filter_efficiency',     '0.999','Ефективність HEPA фільтру')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS discovery.services (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(64) UNIQUE NOT NULL,
    url         VARCHAR(255) NOT NULL,
    healthy     BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
