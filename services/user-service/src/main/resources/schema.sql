CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS profile;

CREATE TABLE IF NOT EXISTS auth.users (
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(255) UNIQUE NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role          VARCHAR(50)  NOT NULL DEFAULT 'operator',
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS profile.user_profiles (
    user_id    BIGINT PRIMARY KEY,
    full_name  VARCHAR(255),
    position   VARCHAR(255),
    department VARCHAR(255),
    phone      VARCHAR(50),
    updated_at TIMESTAMP DEFAULT NOW()
);
