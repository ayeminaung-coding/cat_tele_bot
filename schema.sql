-- ============================================================
-- Telegram Video Bot — Supabase SQL Schema (Redesign)
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- ⚠️ PRODUCTION MIGRATION (Run these lines if updating an existing database):
-- ALTER TABLE videos ADD COLUMN IF NOT EXISTS channel_id BIGINT;
-- CREATE TABLE IF NOT EXISTS config (...); -- see below
-- ============================================================

-- Drop old tables if they exist (ONLY for fresh installs!)
-- WARNING: This will delete all data!
-- DROP TABLE IF EXISTS logs CASCADE;
-- DROP TABLE IF EXISTS payments CASCADE;
-- DROP TABLE IF EXISTS orders CASCADE;
-- DROP TABLE IF EXISTS videos CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TABLE IF EXISTS config CASCADE;

-- ── Users ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username    TEXT,
    first_name  TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'banned')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Videos ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS videos (
    id           VARCHAR PRIMARY KEY,     -- e.g., 'vid_01'
    title        TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'available'
                     CHECK (status IN ('available', 'unavailable')),
    price        INTEGER NOT NULL DEFAULT 1000,
    channel_link TEXT,
    channel_id   BIGINT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Orders ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
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

CREATE INDEX IF NOT EXISTS idx_orders_user_id       ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_admin_msg_id  ON orders(admin_msg_id);
CREATE INDEX IF NOT EXISTS idx_orders_status        ON orders(status);

-- ── Logs ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS logs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type  TEXT NOT NULL,
    admin_id     BIGINT,
    user_id      BIGINT,
    order_id     UUID REFERENCES orders(id) ON DELETE SET NULL,
    detail       TEXT,
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_action_type ON logs(action_type);
CREATE INDEX IF NOT EXISTS idx_logs_user_id     ON logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp   ON logs(timestamp DESC);

-- ── Config (for app settings like bundle text) ───────────────
CREATE TABLE IF NOT EXISTS config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert default bundle text
INSERT INTO config (key, value) VALUES
    ('bundle_info_text', '၁၅ပုဒ်မှာက\n1. လင်တန်းနဲ့ သခင်လေးယွဲ့တို\n2. စစ်သူကြီးကတော်က ကွာရှင်းချင်နေတယ်\n\nဒါလေးတွေ စဆုံးပြီးထားပါတယ်\n15ပုဒ်ပြည့်တဲ့ထိ ဆက်တင်မှာပါ')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- Seed data (Test videos) - Skip if already exists
-- ============================================================
INSERT INTO videos (id, title, status, price) VALUES
('vid_01', 'Myanmar Movie Selection 1', 'available', 1000),
('vid_02', 'Action Blockbuster 2026', 'available', 1000),
('vid_03', 'Comedy Special', 'available', 1000),
('vid_04', 'Exclusive Content (Not Ready)', 'unavailable', 1000)
ON CONFLICT (id) DO NOTHING;
