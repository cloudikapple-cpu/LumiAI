# LumiAI Bot

Production-ready Telegram AI Assistant with multimodal support, web search, user memory, and background task processing.

## Features

- **Multimodal Support**: Text, images, voice messages, videos, and documents
- **Multi-Provider LLM**: OpenRouter, NVIDIA NIM, Groq with automatic fallback
- **Web Search**: Real-time information when needed
- **User Memory**: Persistent memory across conversations
- **Streaming Responses**: Real-time response delivery
- **Background Processing**: Video/document analysis in background workers
- **Rate Limiting**: Built-in spam protection
- **Observability**: Health checks, metrics, structured logging

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TELEGRAM MESSAGE FLOW                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

1. Telegram → Webhook → aiogram Dispatcher
2. Middleware Chain (Rate Limit, Anti-Spam, Session)
3. Handler Classification (text, photo, voice, video, document)
4. Reasoning Pipeline (internal, not shown to user)
   - Query Classification
   - Tool Planning
   - Data Collection
   - Response Synthesis
5. LLM Provider Router (selects best provider by task)
6. Tool Execution (web search, vision, audio, RAG)
7. Memory Layer (short-term Redis, long-term PostgreSQL)
8. Response Delivery (streaming or bulk)
9. Telegram → User
```

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Telegram Bot Token
- At least one LLM API key (OpenRouter, NVIDIA NIM, or Groq)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd lumi-ai-bot

# Install dependencies
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Run with Docker Compose
docker-compose --profile bot up -d
```

### Manual Running

```bash
# Start dependencies
docker-compose up -d postgres redis minio

# Run the bot
python -m app.main --mode bot

# Run the API server
python -m app.main --mode api

# Run background workers
python -m app.main --mode worker
```

## Configuration

All configuration is done through environment variables. See `.env.example` for all options.

### Required Environment Variables

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
OPENROUTER_API_KEY=your_api_key # or NVIDIA_API_KEY or GROQ_API_KEY
```

### Environment Variables Reference

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token from @BotFather | - |
| `OPENROUTER_API_KEY` | Yes* | OpenRouter API key | - |
| `NVIDIA_API_KEY` | Yes* | NVIDIA NIM API key | - |
| `GROQ_API_KEY` | Yes* | Groq API key | - |
| `DATABASE_URL` | No | PostgreSQL connection URL | auto-local |
| `REDIS_URL` | No | Redis connection URL | auto-local |
| `DEBUG` | No | Enable debug mode | false |
| `LOG_LEVEL` | No | Logging level | INFO |

*At least one LLM API key required

## Deploy on Railway

Railway provides the easiest deployment for this application with managed PostgreSQL and Redis.

### Prerequisites

1. [Railway](https://railway.app) account
2. Telegram Bot Token from [@BotFather](https://t.me/BotFather)
3. OpenRouter API key (recommended)

### Steps

#### 1. Create Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init

# Or connect to GitHub repo for automatic deployments
```

#### 2. Add Database and Redis

```bash
# Add PostgreSQL plugin
railway add postgresql

# Add Redis plugin
railway add redis

# These will automatically set DATABASE_URL and REDIS_URL
```

#### 3. Configure Environment Variables

In Railway dashboard, add these variables:

| Variable | Value |
|----------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token |
| `OPENROUTER_API_KEY` | Your API key |
| `DEBUG` | `false` |
| `LOG_LEVEL` | `INFO` |

#### 4. Deploy

```bash
# Deploy via GitHub (recommended)
# Connect your repo in Railway dashboard
# Push to main branch triggers deployment

# Or deploy via CLI
railway up
```

#### 5. Start Command

In Railway settings, set the start command:

```bash
python -m app.main --mode bot
```

### Health Check

The application exposes health endpoints:
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe

Railway uses `/api/v1/health/live` for health checks automatically.

### Scaling Workers (Optional)

For heavy video/document processing, deploy a separate worker:

1. Create a second Railway service
2. Set start command: `python -m app.main --mode worker`
3. Share same `DATABASE_URL` and `REDIS_URL`

## Local Development

### With Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop all services
docker-compose down
```

### Without Docker

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Start PostgreSQL and Redis (example with Docker)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine

# 3. Copy and edit environment
cp .env.example .env

# 4. Initialize database
python -c "import asyncio; from app.db.base import init_db, init_tables; asyncio.run(init_db()); asyncio.run(init_tables())"

# 5. Run the bot
python -m app.main --mode bot
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help message |
| `/settings` | Configure settings |
| `/reset` | Clear conversation context |
| `/memory` | View your stored memory |
| `/forget` | Delete all memory |
| `/forget_last` | Delete last conversation |
| `/mode` | Change assistant mode |
| `/about` | About LumiAI |

### Assistant Modes

- **assistant** - Balanced responses (default)
- **explorer** - Deep research, more details
- **concise** - Brief, to-the-point answers

## API Endpoints

### Health Check
```
GET /api/v1/health
GET /api/v1/health/live
GET /api/v1/health/ready
```

### Admin (protected in production)
```
GET /api/v1/admin/stats
POST /api/v1/admin/cache/clear
GET /api/v1/admin/users/{user_id}
```

### Metrics
```
GET /api/v1/metrics
GET /api/v1/metrics/prometheus
```

## Development

```bash
# Run tests
pytest

# Run linting
ruff check .

# Run type checking
mypy app/
```

## Project Structure

```
lumi-ai-bot/
├── app/
│   ├── main.py           # Entry point
│   ├── config.py         # Configuration
│   ├── logging.py        # Logging setup
│   ├── core/             # Core interfaces and types
│   ├── db/               # Database layer
│   ├── llm/              # LLM providers and routing
│   ├── tools/            # Tool layer (web search, vision, etc.)
│   ├── memory/           # Memory management
│   ├── workers/          # Background task processing
│   ├── services/         # Business logic
│   ├── telegram/         # Telegram bot handlers
│   ├── api/              # FastAPI server
│   └── utils/            # Utilities
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile            # Production Docker image
└── .env.example          # Environment variables example
```

## License

MIT