# Redis Cache Example

This tutorial shows a cache-aside workflow using PolePosition's Redis
integration.

The target endpoint:

```text
GET /api/v1/quotes/{topic}
```

The first request computes a quote and stores it in Redis. Repeated requests for
the same topic return the cached value.

Complete runnable source:
[examples/redis-cache/app](https://github.com/polepos/poleposition/tree/main/examples/redis-cache/app)

## Create the Project

```bash
polepos start redis-cache --db none
cd redis-cache
cp .env.example .env
uv sync --extra dev
```

## Add Redis

```bash
polepos add integration redis
uv sync --extra dev
```

Use these `.env` values:

```env
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
REDIS_CLIENT_NAME=redis_cache
REDIS_KEY_PREFIX=redis_cache
REDIS_SOCKET_TIMEOUT_SECONDS=5.0
```

Run Redis locally:

```bash
docker compose -f compose.redis.yaml up -d
```

The full source scenario includes the compose file.

## Add the Module

```bash
polepos add module quotes --api-only
```

Reshape the generated files:

- `schemas.py` defines `QuoteResponse`
- `services/quotes_service.py` implements cache-aside logic
- `router.py` exposes `GET /api/v1/quotes/{topic}`

The service should depend on a small cache protocol, call `get_text()` first,
compute on a miss, and then call `set_text(..., ttl_seconds=300)`.

Run FastAPI:

```bash
uv run python -m redis_cache.run
```

Call twice:

```bash
curl http://localhost:8000/api/v1/quotes/fastapi
curl http://localhost:8000/api/v1/quotes/fastapi
```

The first response should report `"cache": "miss"`. The second should report
`"cache": "hit"`.

## Why This Shape

- Redis stays an implementation detail behind the module service.
- The response includes cache status only so the tutorial is easy to verify.
- The key prefix prevents collisions when several apps share one Redis database.
- Unit tests use `build_in_memory_redis_cache()` and do not need Docker.

Validate:

```bash
uv run pytest
polepos check
```

Full source scenario:
[examples/redis-cache](https://github.com/polepos/poleposition/blob/main/examples/redis-cache/README.md)
