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
python -m uvicorn main:app --reload --port 8000
```

### 6. Deploy to production (Google Cloud Run)

Since the bot uses background queues to process webhooks concurrently, **Cloud Run must be configured with "CPU always allocated" (`--no-cpu-throttling`)**. If CPU is throttled after the webhook returns, the background tasks will freeze.

```bash
# 1. Build and deploy to Cloud Run
gcloud run deploy telegram-vip-bot \
  --source . \
  --allow-unauthenticated \
  --cpu 1 \
  --memory 512Mi \
  --no-cpu-throttling \
  --min-instances 1 \
  --max-instances 10

# 2. Set all Environment Variables in the Cloud Console
# Make sure to set REDIS_URL if you are scaling past 1 instance
# Make sure to grab the newly generated Service URL and update WEBHOOK_URL!
```

### 7. Other Platforms (Railway / Render / Fly.io)
```bash
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
| `REDIS_URL` | ❌ | Redis connection URL for shared session state (recommended in production) |
| `UPDATE_WORKERS` | ❌ | Background workers for webhook update processing (default: 8) |
| `UPDATE_QUEUE_SIZE` | ❌ | Max queued webhook updates before returning 503 (default: 1000) |
| `BROADCAST_BATCH_SIZE` | ❌ | Number of users per broadcast batch (default: 20) |
| `BROADCAST_BATCH_DELAY_SECONDS` | ❌ | Delay between broadcast batches in seconds (default: 0.4) |

### Production tuning notes

- Use a stable domain for `WEBHOOK_URL` (avoid temporary ngrok URLs in production).
- Set `REDIS_URL` when running multiple app instances/workers.
- Start with `UPDATE_WORKERS=8` and `UPDATE_QUEUE_SIZE=1000`, then tune using real traffic metrics.

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

## Commands List

### 👤 User Commands
| Command | Description |
|---|---|
| `/start` | Start the bot, register the user, and show the main purchase menu. |
| *(Any Text)* | If a user types text instead of clicking a button, it is forwarded to the Admin Group as a **Support Ticket**. |

### 🛠️ Admin Commands (Must be in `ADMIN_IDS`)
| Command | Description |
|---|---|
| `/addvideo` | Start an interactive flow to add a new video to the single-purchase list. Asks for Title, then Price. |
| `/deletevideo` | Open an inline list of all currently available videos to select and delete them from the database. |
| `/setvideolink` | Set the target Telegram invite/channel link for a specific video. When users buy this video, they receive this link automatically upon approval. |
| `/setbundletext` | Update the text displayed when a user clicks the "Bundle" purchase option. |
| `/userstats` | View a quick statistical report of the total number of users and users who joined today. |
| `/broadcast` | Start admin broadcast flow with selectable user segments (all, paid, no-order, single buyers, bundle buyers). |
| `/cancel` | Cancel any ongoing admin flow (adding, deleting, link setting) without saving. |
| *(Reply to Support)* | If an admin **Replies** to a Support Ticket or Payment inside the Admin Group with Text, Photo, or Video, the bot will secretly copy and forward that reply directly to the User's DM! |

---
