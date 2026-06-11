# RabbitMQ Quick Start Example

This tutorial mirrors the Kafka quick start, but uses RabbitMQ's exchange and
queue model.

The target workflow:

```text
POST /api/v1/greetings/send
```

The endpoint publishes a greeting message. A separate worker consumes the queue
and prints the message.

Complete runnable source:
[examples/rabbitmq-quick-start/app](https://github.com/polepos/poleposition/tree/main/examples/rabbitmq-quick-start/app)

## Create the Project

```bash
polepos start rabbitmq-quick-start --db none
cd rabbitmq-quick-start
cp .env.example .env
uv sync --extra dev
```

## Add RabbitMQ

```bash
polepos add integration rabbitmq
uv sync --extra dev
```

Use these `.env` values:

```env
RABBITMQ_ENABLED=true
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_CLIENT_ID=rabbitmq_quick_start
RABBITMQ_EXCHANGE=greetings.events
RABBITMQ_EXCHANGE_TYPE=topic
RABBITMQ_EXCHANGE_DURABLE=true
RABBITMQ_DEFAULT_ROUTING_KEY=greetings.created
RABBITMQ_DEFAULT_QUEUE=greetings.demo
RABBITMQ_QUEUE_DURABLE=true
RABBITMQ_PREFETCH_COUNT=10
```

Run RabbitMQ locally:

```bash
docker compose -f compose.rabbitmq.yaml up -d
```

The full source scenario includes the compose file.

## Add the Module

```bash
polepos add module greetings --api-only
```

Reshape the generated files:

- `schemas.py` defines `GreetingRequest` and `GreetingResponse`
- `services/greetings_service.py` builds a generated `RabbitMQMessage`
- `router.py` exposes `POST /api/v1/greetings/send`
- `consumer.py` consumes messages with `consume_json_messages`

The service depends on a small publisher protocol so unit tests can use
`InMemoryRabbitMQEventPublisher` without connecting to a broker.

Run FastAPI:

```bash
uv run python -m rabbitmq_quick_start.run
```

Run the worker:

```bash
uv run python -m rabbitmq_quick_start.modules.greetings.consumer
```

Publish a message:

```bash
curl -X POST http://localhost:8000/api/v1/greetings/send \
  -H "Content-Type: application/json" \
  -d '{"recipient":"team","message":"Hello, PolePosition RabbitMQ!"}'
```

Expected worker output:

```text
got: Hello, PolePosition RabbitMQ!
```

## Why This Shape

- RabbitMQ consumption is worker work, not request-serving work.
- The API returns `202 Accepted` because processing happens asynchronously.
- The queue binding lives in runtime settings so environments can change routing
  without rewriting module logic.
- Fast tests use the generated in-memory publisher; broker tests can live in a
  separate Docker/Testcontainers suite.

Validate:

```bash
uv run pytest
polepos check
```

Full source scenario:
[examples/rabbitmq-quick-start](https://github.com/polepos/poleposition/blob/main/examples/rabbitmq-quick-start/README.md)
