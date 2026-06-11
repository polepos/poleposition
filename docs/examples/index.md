# Examples

Examples show the next step after project generation: what to keep, what to
rewrite, and how PolePosition's structure supports a real workflow.

## Available Examples

### User Registration

Shows how to turn a generated module into a real user registration REST API
with command flow, file-by-file edits, password hashing, tests, and migration
checks.

Focus:

- `polepos start account-api`
- `polepos add module users`
- `POST /api/v1/users/register`
- module-local model, schema, repository, services, router, and test changes
- Alembic migration review

Read the site guide: [User Registration](user-registration.md)

### Auth Foundation

Shows how the generated JWT authentication foundation protects routes before a
full login system exists.

Focus:

- public versus protected endpoints
- JWT-based current user resolution
- role-gated route examples
- local token generation for testing

Read the site guide: [Auth Foundation](auth-foundation.md)

Source scenario:
[examples/auth-foundation](https://github.com/polepos/poleposition/blob/main/examples/auth-foundation/README.md)

### HTML Swap

Shows how a generated module can be reshaped into a focused transformation
endpoint backed by PostgreSQL history.

Focus:

- `polepos add module html --api-only`
- rewriting a generated module for a real endpoint contract
- PostgreSQL-backed swap history
- `POST /api/v1/html/swap`

Read the site guide: [HTML Swap](html-swap.md)

Source scenario:
[examples/html-swap](https://github.com/polepos/poleposition/blob/main/examples/html-swap/README.md)

### Kafka Quick Start

Shows how to adapt a minimal Spring Kafka producer/listener demo into a
PolePosition FastAPI project with an explicit Kafka integration and a
module-local consumer worker.

Focus:

- `polepos start kafka-quick-start --db none`
- complete runnable source under `examples/kafka-quick-start/app`
- `polepos add integration kafka`
- `polepos add module greetings --api-only`
- `POST /api/v1/greetings/send`
- broker-free unit testing with `InMemoryKafkaEventProducer`

Read the site guide: [Kafka Quick Start](kafka-quick-start.md)

Source scenario:
[examples/kafka-quick-start](https://github.com/polepos/poleposition/blob/main/examples/kafka-quick-start/README.md)

### RabbitMQ Quick Start

Shows the same first-message workflow using RabbitMQ's exchange and queue
model instead of Kafka topics.

Focus:

- `polepos start rabbitmq-quick-start --db none`
- complete runnable source under `examples/rabbitmq-quick-start/app`
- `polepos add integration rabbitmq`
- `polepos add module greetings --api-only`
- `POST /api/v1/greetings/send`
- broker-free unit testing with `InMemoryRabbitMQEventPublisher`

Read the site guide: [RabbitMQ Quick Start](rabbitmq-quick-start.md)

Source scenario:
[examples/rabbitmq-quick-start](https://github.com/polepos/poleposition/blob/main/examples/rabbitmq-quick-start/README.md)

### Redis Cache

Shows how to add Redis and reshape an API-only module into a cache-aside
workflow.

Focus:

- `polepos start redis-cache --db none`
- complete runnable source under `examples/redis-cache/app`
- `polepos add integration redis`
- `polepos add module quotes --api-only`
- `GET /api/v1/quotes/{topic}`
- in-memory cache testing with `build_in_memory_redis_cache`

Read the site guide: [Redis Cache](redis-cache.md)

Source scenario:
[examples/redis-cache](https://github.com/polepos/poleposition/blob/main/examples/redis-cache/README.md)

### OpenAI Prompt

Shows how to turn the provider-agnostic AI prompt template into a working
OpenAI-backed endpoint.

Focus:

- `polepos start openai-prompt --db none`
- complete runnable source under `examples/openai-prompt/app`
- `polepos add module assistant --template ai-prompt`
- implementing `integrations/llm/openai_client.py`
- `POST /api/v1/assistant/respond`
- stub-provider unit testing without live API calls

Read the site guide: [OpenAI Prompt](openai-prompt.md)

Source scenario:
[examples/openai-prompt](https://github.com/polepos/poleposition/blob/main/examples/openai-prompt/README.md)
