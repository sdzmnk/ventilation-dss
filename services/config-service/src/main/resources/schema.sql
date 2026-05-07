CREATE SCHEMA IF NOT EXISTS configuration;

CREATE TABLE IF NOT EXISTS configuration.parameters (
    id          BIGSERIAL PRIMARY KEY,
    key         VARCHAR(255) UNIQUE NOT NULL,
    value       JSONB,
    description TEXT,
    updated_at  TIMESTAMP DEFAULT NOW()
);
