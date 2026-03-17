# Telegram VIP Bot 🤖

Production-ready Telegram VIP subscription bot — **Python + FastAPI + Supabase**.

Myanmar-language UX | KBZPay payments | Admin group approval | Unique invite links

---

## Features

- 🇲🇲 Myanmar-only UI with inline button menus
- 💳 KBZPay screenshot submission & verification
- 👥 Admin group approval with ✅/❌ inline buttons
- 🔗 One-use VIP invite link (24h expiry) generated on approval
- 📨 Admin ↔ User text forwarding via reply threads
- 🔒 Admin ID whitelist, duplicate approval guard, banned user check
- 📁 Supabase Storage for screenshots (signed URLs, 5MB limit)
- 🔄 Webhook mode (FastAPI) — production-ready

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Setup Supabase
1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** → paste and run `schema.sql`
3. Go to **Storage** → create a bucket named `screenshots` (private)
4. Copy your **Project URL** and **Service Role Key** to `.env`

### 4. Bot setup
1. Create a bot via [@BotFather](https://t.me/BotFather) → get `BOT_TOKEN`
2. Add bot to your **Admin Group** (must be able to send messages)
3. Add bot to **VIP Channel/Group** as **Administrator** with "Invite Users via Link" permission
4. Set `ADMIN_GROUP_ID`, `VIP_CHANNEL_ID`, `ADMIN_IDS` in `.env`

### 5. Run locally (with ngrok)
```bash
# Terminal 1 — expose local port
ngrok http 8000
# Copy the https URL → set as WEBHOOK_URL in .env

# Terminal 2 — start bot
uvicorn main:app --reload --port 8000
```

### 6. Deploy to production
```bash
# Railway / Render / Fly.io
# Set all environment variables in the platform dashboard
# Start command:
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## Project Structure

```
telegram_vip_bot/
├── main.py               # FastAPI app + webhook endpoint
├── bot_app.py            # PTB Application + handler registration
├── config.py             # Settings / env validation
├── schema.sql            # Supabase DB schema (run once)
├── requirements.txt
├── .env.example
├── db/
│   ├── client.py         # Supabase client singleton
│   ├── users.py          # User CRUD
│   ├── payments.py       # Payment CRUD
│   ├── logs.py           # Action logger
│   └── storage.py        # Screenshot uploader
├── data/
│   ├── plans.py          # VIP plan definitions
│   ├── messages.py       # All Myanmar messages
│   └── keyboards.py      # Inline keyboard builders
├── handlers/
│   ├── user_handler.py   # /start, plan selection
│   ├── payment_handler.py# Screenshot upload flow
│   ├── admin_handler.py  # Forward to admin, approve/reject
│   ├── invite_handler.py # Generate + send VIP invite link
│   ├── message_router.py # Admin reply → user forwarding
│   └── error_handler.py  # Global error handling
└── utils/
    ├── session.py        # Async in-memory session state
    ├── unique_amount.py  # Per-user unique payment amount
    └── retry.py          # Telegram API retry wrapper
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram bot token from @BotFather |
| `WEBHOOK_URL` | ✅ | Public HTTPS URL (no trailing slash) |
| `ADMIN_GROUP_ID` | ✅ | Admin review group chat ID (negative) |
| `VIP_CHANNEL_ID` | ✅ | VIP channel/group ID (negative) |
| `ADMIN_IDS` | ✅ | Comma-separated admin Telegram user IDs |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | ✅ | Supabase service role key |
| `KBZPAY_PHONE` | ✅ | KBZPay phone number shown to users |
| `KBZPAY_NAME` | ✅ | KBZPay account name shown to users |
| `PORT` | ❌ | Server port (default: 8000) |
| `USE_UNIQUE_AMOUNT` | ❌ | Unique amount offset (default: true) |
| `MAX_FILE_SIZE` | ❌ | Max screenshot size bytes (default: 5MB) |

---

## User Flow

```
/start
  └─→ Welcome + "View Plans" button
        └─→ Plan list (1m / 3m / Lifetime)
              └─→ Select plan → KBZPay instructions + unique amount
                    └─→ Upload screenshot
                          └─→ "Payment received, under review" ✅
                                └─→ Admin group: screenshot + Approve/Reject
                                      ├─→ ✅ Approve → User gets VIP invite link 🎉
                                      └─→ ❌ Reject → User gets rejection + Retry button
```

---

## VIP Plans (edit in `data/plans.py`)

| Plan | Price | Duration |
|---|---|---|
| တစ်လ (1 Month) | 5,000 MMK | 30 days |
| သုံးလ (3 Months) | 12,000 MMK | 90 days |
| တစ်သက်တာ (Lifetime) | 30,000 MMK | Forever |
