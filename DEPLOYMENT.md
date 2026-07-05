# Deployment Guide

## Current Production Deployment

| Resource | Value |
|---|---|
| **Platform** | Azure Container Apps |
| **Region** | Southeast Asia |
| **URL** | `https://telegram-vip-bot.bravebeach-b93d3664.southeastasia.azurecontainerapps.io` |
| **Container Registry** | `tgvipbotacr.azurecr.io` |
| **Image** | `tgvipbotacr.azurecr.io/telegram-vip-bot:latest` |
| **Resource Group** | `rg-telegram-vip-bot` |
| **Container Apps Environment** | `telegram-bot-env` |
| **CPU / Memory** | 1.0 vCPU / 2 GiB |
| **Min / Max Replicas** | 1 / 3 |
| **Supabase** | `uncmdofctlconluncsjx.supabase.co` |
| **Session Store** | In-memory (single-instance) |

## Environment Variables

| Variable | Source |
|---|---|
| `BOT_TOKEN` | @BotFather |
| `WEBHOOK_URL` | Set to the app URL (no trailing slash) |
| `ADMIN_GROUP_ID` | Admin review group chat |
| `VIP_CHANNEL_ID` | VIP channel/group |
| `DISCUSSION_GROUP_ID` | Giveaway discussion group |
| `ADMIN_IDS` | Comma-separated Telegram admin IDs |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (keep secret) |
| `KBZPAY_PHONE` | KBZPay account phone |
| `KBZPAY_NAME` | KBZPay account name |
| `USE_UNIQUE_AMOUNT` | `true` |
| `MAX_FILE_SIZE` | `5242880` |
| `UPDATE_WORKERS` | `8` |
| `ADMIN_REVIEW_TIME_HOURS` | `1` |

## How to Deploy

### Prerequisites

- Azure CLI (`az`) logged into the target subscription
- Docker Desktop (for local builds)

### Build & Push

```bash
# Login to ACR
az acr credential show --name tgvipbotacr --resource-group rg-telegram-vip-bot --query passwords[0].value --output tsv | docker login tgvipbotacr.azurecr.io -u tgvipbotacr --password-stdin

# Build image
docker build -t tgvipbotacr.azurecr.io/telegram-vip-bot:latest .

# Push to ACR
docker push tgvipbotacr.azurecr.io/telegram-vip-bot:latest
```

### Deploy New Revision

```bash
az containerapp update `
  --name telegram-vip-bot `
  --resource-group rg-telegram-vip-bot `
  --image tgvipbotacr.azurecr.io/telegram-vip-bot:latest
```

### Update Environment Variables

```bash
# Set a single variable
az containerapp update `
  --name telegram-vip-bot `
  --resource-group rg-telegram-vip-bot `
  --set-env-vars KEY="value"

# Remove a variable
az containerapp update `
  --name telegram-vip-bot `
  --resource-group rg-telegram-vip-bot `
  --remove-env-vars KEY
```

### Update Webhook (after URL change)

```powershell
$TOKEN = "<BOT_TOKEN>"
$body = @{url = "https://<NEW_URL>/webhook"} | ConvertTo-Json
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TOKEN/setWebhook" -Method Post -ContentType "application/json" -Body $body
```

### Check Logs

```bash
az containerapp logs show --name telegram-vip-bot --resource-group rg-telegram-vip-bot --type console --tail 50
```

### Health Check

```bash
curl https://telegram-vip-bot.bravebeach-b93d3664.southeastasia.azurecontainerapps.io/health
```

## Migration (Azure Student Plan -> New Account)

If you need to migrate to a new Azure student account again:

1. **Login to new account**: `az login`
2. **Create infrastructure** in the new subscription:
   - Resource Group, ACR, Container Apps Environment
3. **Build & push image** to the new ACR
4. **Deploy Container App** with all env vars (keep `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` the same)
5. **Set Telegram webhook** to the new URL
6. **Verify health** endpoint
7. **Clean up** old resources if the subscription is still active

## Notes

- Supabase (database + storage) is hosted separately from Azure and does not need migration
- Redis was previously used via Upstash but is no longer available — session state uses in-memory storage
- The old Azure account (`ayeminaung.mf@gmail.com`) subscription is disabled; resources are abandoned
