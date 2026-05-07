CREATE SCHEMA IF NOT EXISTS chat;
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(255) UNIQUE NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role          VARCHAR(50) NOT NULL DEFAULT 'operator',
    is_active     BOOLEAN     NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS chat.rooms (
    id         BIGSERIAL PRIMARY KEY,
    name       VARCHAR(255) UNIQUE,
    is_dm      BOOLEAN   NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat.dm_participants (
    room_id BIGINT NOT NULL REFERENCES chat.rooms(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    PRIMARY KEY (room_id, user_id)
);

CREATE TABLE IF NOT EXISTS chat.messages (
    id         BIGSERIAL PRIMARY KEY,
    room_id    BIGINT    NOT NULL REFERENCES chat.rooms(id) ON DELETE CASCADE,
    user_id    BIGINT,
    username   VARCHAR(255),
    body       TEXT      NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
