-- PostgreSQL schema for Telegram Intake Bot session persistence.
-- Used only when SESSION_STORAGE_TYPE=postgres.

CREATE TABLE IF NOT EXISTS tib_sessions (
    user_id BIGINT PRIMARY KEY,
    state JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tib_sessions_updated_at
    ON tib_sessions (updated_at);
