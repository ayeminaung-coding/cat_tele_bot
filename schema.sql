-- ============================================================
-- Telegram Video Bot — Supabase SQL Schema (Redesign)
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- Drop old tables if they exist (Migration)
DROP TABLE IF EXISTS logs CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS videos CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ── Users ────────────────────────────────────────────────────
CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    username    TEXT,
    first_name  TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'banned')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Videos ───────────────────────────────────────────────────
CREATE TABLE videos (
    id          VARCHAR PRIMARY KEY,     -- e.g., 'vid_01'
    title       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'available'
                    CHECK (status IN ('available', 'unavailable')),
    price       INTEGER NOT NULL DEFAULT 1000,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Orders ───────────────────────────────────────────────────
CREATE TABLE orders (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    type           TEXT NOT NULL CHECK (type IN ('single', 'bundle')),
    video_id       VARCHAR REFERENCES videos(id) ON DELETE SET NULL, -- Null if bundle
    amount         INTEGER NOT NULL,
    screenshot_url TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'approved', 'rejected')),
    admin_msg_id   INTEGER,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_user_id       ON orders(user_id);
CREATE INDEX idx_orders_admin_msg_id  ON orders(admin_msg_id);
CREATE INDEX idx_orders_status        ON orders(status);

-- ── Logs ─────────────────────────────────────────────────────
CREATE TABLE logs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type  TEXT NOT NULL,
    admin_id     BIGINT,
    user_id      BIGINT,
    order_id     UUID REFERENCES orders(id) ON DELETE SET NULL,
    detail       TEXT,
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_logs_action_type ON logs(action_type);
CREATE INDEX idx_logs_user_id     ON logs(user_id);
CREATE INDEX idx_logs_timestamp   ON logs(timestamp DESC);

-- ============================================================
-- Seed data (Test videos)
-- ============================================================
INSERT INTO videos (id, title, status, price) VALUES
('vid_01', 'Myanmar Movie Selection 1', 'available', 1000),
('vid_02', 'Action Blockbuster 2026', 'available', 1000),
('vid_03', 'Comedy Special', 'available', 1000),
('vid_04', 'Exclusive Content (Not Ready)', 'unavailable', 1000);
