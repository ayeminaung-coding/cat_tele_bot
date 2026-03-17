-- ============================================================
-- Telegram VIP Bot — Supabase SQL Schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- ── Users ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username    TEXT,
    first_name  TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('active', 'pending', 'banned')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Payments ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    plan_id        TEXT NOT NULL,
    amount         INTEGER NOT NULL,
    screenshot_url TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'approved', 'rejected')),
    admin_msg_id   INTEGER,          -- message_id in admin group
    invite_link    TEXT,             -- filled after approval
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_user_id       ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_admin_msg_id  ON payments(admin_msg_id);
CREATE INDEX IF NOT EXISTS idx_payments_status        ON payments(status);

-- ── Logs ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS logs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type  TEXT NOT NULL,
    admin_id     BIGINT,
    user_id      BIGINT,
    payment_id   UUID REFERENCES payments(id) ON DELETE SET NULL,
    detail       TEXT,
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_action_type ON logs(action_type);
CREATE INDEX IF NOT EXISTS idx_logs_user_id     ON logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp   ON logs(timestamp DESC);

-- ============================================================
-- Supabase Storage: create "screenshots" bucket
-- Run this OR create the bucket manually in Storage UI
-- ============================================================
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('screenshots', 'screenshots', false)
-- ON CONFLICT DO NOTHING;
