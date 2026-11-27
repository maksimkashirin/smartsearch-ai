CREATE TABLE IF NOT EXISTS search_events (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    requested_mode TEXT NOT NULL,
    actual_mode TEXT NOT NULL,
    intent TEXT,
    result_count INTEGER NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_search_events_created
ON search_events(created_at);
