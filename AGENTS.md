# AGENTS.md - Instructions for Future AI Agents

This file contains instructions for working with this codebase.

## Project Overview

LumiAI is a production-ready Telegram AI assistant with multimodal support. The architecture follows clean separation of concerns with distinct layers.

## Key Architecture Decisions

### Framework Choice: aiogram 3.x
- **Why**: Fully async, lightweight, good middleware support
- **Alternative considered**: python-telegram-bot 21+ (more verbose)

### Database: SQLAlchemy 2 async + asyncpg
- **Why**: ORM abstraction with async support, Alembic migrations
- **Alternative**: Raw asyncpg (less abstraction)

### Background Queue: arq
- **Why**: Native asyncio, built-in retry/circuit breaker, Redis-based
- **Alternative**: Celery (overkill), RQ (less features)

### Memory Strategy
- **Short-term**: Redis (fast, ephemeral)
- **Long-term**: PostgreSQL (persistent, queryable)

## Critical Implementation Details

### Provider Pattern
All LLM providers implement `BaseLLMProvider` interface. To add a new provider:
1. Create `app/llm/providers/<provider_name>.py`
2. Inherit from `BaseLLMProvider`
3. Implement `chat()`, `chat_stream()`, `healthcheck()`
4. Register in `app/llm/router.py:create_router()`

### Tool Pattern
All tools implement `BaseTool` interface. To add a new tool:
1. Create `app/tools/<tool_name>.py`
2. Inherit from `BaseTool`
3. Implement `execute()`, `name`, `description`, `input_schema`
4. Register in `app/tools/registry.py:_register_default_tools()`

### Message Flow (CRITICAL)
1. Telegram → aiogram Dispatcher
2. Middlewares (rate limit, session, anti-spam)
3. Handlers (text, photo, voice, video, document, commands)
4. Services (ChatService, MultimodalService, ReasoningPipeline)
5. LLM Router → Provider
6. Tools (if needed)
7. Memory (update)
8. Response → Telegram

### Environment Variables
All config via `.env` + pydantic-settings. No hardcoded values.

## Coding Conventions

1. **Typings**: Use type hints everywhere
2. **Async**: All I/O operations must be async (no blocking in event loop)
3. **Error Handling**: Use custom exceptions from `core.exceptions`
4. **Logging**: Use `get_logger(__name__)` from `app.logging`
5. **No secrets in logs**: Never log API keys or tokens

## Testing Strategy

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest app/tests/unit/test_llm_router.py
```

## Common Tasks

### Adding a new LLM provider
1. Create provider class in `app/llm/providers/`
2. Add model info to `available_models` property
3. Implement required methods
4. Register in router's `create_router()`

### Adding a new tool
1. Create tool class in `app/tools/`
2. Implement interface (name, description, input_schema, execute)
3. Register in `app/tools/registry.py:_register_default_tools()`

### Modifying the reasoning pipeline
- Edit `app/services/reasoning.py:ReasoningPipeline`
- The pipeline is internal - never expose chain-of-thought to users

### Changing memory policy
- Edit `app/memory/policies.py:DefaultMemoryPolicy`
- Adjust TTL constants based on memory importance

## Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add user preferences table"

# Apply migrations
alembic upgrade head
```

## Docker Commands

```bash
# Build image
docker build -t lumiai-bot .

# Run with compose
docker-compose --profile bot up -d

# Run worker
docker-compose --profile worker up -d

# View logs
docker-compose logs -f bot
```

## Performance Considerations

1. **Long operations → background**: Video processing, large document analysis
2. **Rate limiting**: Protect against spam and API abuse
3. **Context compression**: Automatic when dialog exceeds threshold
4. **Connection pooling**: Redis and PostgreSQL connection pools configured

## Security Notes

1. API keys in environment variables only
2. Rate limiting enabled by default
3. Anti-spam middleware checks for common patterns
4. No user data shared with third parties
5. Webhook uses secret token verification

## Debugging

```bash
# Enable debug mode
DEBUG=true LOG_LEVEL=DEBUG python -m app.main --mode bot

# Check logs
tail -f logs/lumi-ai-$(date +%Y-%m-%d).log
```

## Deployment Checklist

1. Set all required environment variables
2. Run database migrations
3. Configure Telegram webhook or use polling
4. Set up monitoring (health endpoints)
5. Configure Redis persistence
6. Set up backup for PostgreSQL