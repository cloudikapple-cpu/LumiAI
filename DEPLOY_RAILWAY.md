# Deploying LumiAI Bot on Railway

This guide provides step-by-step instructions for deploying LumiAI Bot on Railway.

## Why Railway?

- **Managed PostgreSQL & Redis** - No need to manage databases yourself
- **Docker Native** - Your Dockerfile works as-is
- **Automatic HTTPS** - SSL certificates handled automatically
- **Health Checks** - Built-in support for liveness/readiness probes
- **Preview Environments** - Test changes before merging to main

## Deployment Steps

### 1. Prepare Your Repository

Push your code to GitHub. Railway will automatically detect the Dockerfile.

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/lumi-ai-bot.git
git push -u origin main
```

### 2. Create Railway Project

Option A: Via Railway Dashboard
1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository

Option B: Via CLI
```bash
npm install -g @railway/cli
railway login
railway init
railway link
```

### 3. Add PostgreSQL Database

```bash
railway add postgresql
```

This creates a PostgreSQL instance and automatically sets `DATABASE_URL` environment variable.

### 4. Add Redis Cache

```bash
railway add redis
```

This creates a Redis instance and automatically sets `REDIS_URL` environment variable.

### 5. Configure Environment Variables

In Railway Dashboard → Your Project → Variables, add:

| Variable | Value | Notes |
|----------|-------|-------|
| `TELEGRAM_BOT_TOKEN` | `your_bot_token` | Get from @BotFather |
| `OPENROUTER_API_KEY` | `sk-or-...` | Get from openrouter.ai/keys |
| `DEBUG` | `false` | |
| `LOG_LEVEL` | `INFO` | |
| `WEBHOOK_DOMAIN` | `https://your-project.up.railway.app` | Optional, for webhook mode |

### 6. Deploy

Deployment starts automatically when you push to GitHub.

To deploy manually:
```bash
railway up
```

### 7. Verify Deployment

Check the health endpoint:
```bash
curl https://your-project.up.railway.app/api/v1/health/live
```

### 8. Configure Telegram Webhook (Optional)

For production, use webhook mode instead of polling:

```bash
# Set webhook
curl -F "url=https://your-project.up.railway.app/webhook" \
  https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook
```

## Architecture on Railway

```
┌─────────────────────────────────────────────────────────────────┐
│                        Railway                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  LumiAI Bot Service                       │  │
│  │                  (Docker container)                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│  │  │ Telegram    │  │ FastAPI     │  │ Background      │   │  │
│  │  │ Bot         │  │ (health,    │  │ Worker (arq)    │   │  │
│  │  │ (aiogram)   │  │ admin)      │  │                 │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│         │                    │                    │             │
│         ▼                    ▼                    ▼             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐    │
│  │ PostgreSQL  │      │ PostgreSQL  │      │   Redis     │    │
│  │ (Plugin)    │      │ (Plugin)    │      │ (Plugin)    │    │
│  └─────────────┘      └─────────────┘      └─────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Scaling Considerations

### Current Architecture
- Bot + API + Worker run in single container (`--mode all`)
- All share same PostgreSQL and Redis

### For High Load

1. **Separate Worker Service**
   - Create second Railway service
   - Start command: `python -m app.main --mode worker`
   - Shares `DATABASE_URL` and `REDIS_URL`

2. **Read Replicas**
   - Add read replica PostgreSQL
   - Update `DATABASE_URL` to point to replica

3. **Multiple Bot Instances**
   - Note: Telegram doesn't support distributed bots without fanout
   - Consider this only for webhook mode with message queuing

## Troubleshooting

### Bot not responding

1. Check logs: `railway logs`
2. Verify `TELEGRAM_BOT_TOKEN` is correct
3. Check health: `https://your-project.up.railway.app/api/v1/health/ready`

### Database connection errors

1. Verify `DATABASE_URL` is set: `railway variables`
2. Check PostgreSQL is active in Railway dashboard
3. Check logs for connection timeout

### Memory issues

1. Upgrade Railway plan for more RAM
2. Reduce `WORKER_CONCURRENCY` in environment variables

## Environment Variables on Railway

Railway automatically provides:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection | `redis://host:6379/0` |
| `PORT` | HTTP port | `8443` |
| `RAILWAY_ENVIRONMENT` | Environment name | `production` |

Your application uses `DATABASE_URL` and `REDIS_URL` directly.

## Security Notes

1. **Never commit `.env`** - Already in `.gitignore`
2. **Use Railway secrets** - Store API keys in Railway Variables, not `.env`
3. **Webhook verification** - Telegram uses fixed token for webhook verification
4. **Rate limiting** - Built-in rate limiting protects against spam

## Useful Railway Commands

```bash
# View logs
railway logs

# Open shell in container
railway shell

# Check environment variables
railway variables

# Connect to PostgreSQL
railway run psql

# Redeploy
railway up --prod

# Rollback
railway rollback
```

## Cost Estimation

- **Hobby**: ~$5/month (1GB RAM, shared CPU)
- **Pro**: ~$20/month (2GB RAM, dedicated CPU)

Add-ons:
- PostgreSQL: included in hobby tier
- Redis: ~$5/month

Total: ~$5-25/month depending on usage.