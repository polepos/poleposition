# Kafka Quick Start Example

This scenario adapts the producer/listener idea from
[Dan Vega's Spring Kafka quick start](https://github.com/danvega/spring-kafka-quick-start)
to a PolePosition-generated FastAPI project.

The target workflow:

```text
POST /api/v1/greetings/send
```

The endpoint publishes a greeting event to Kafka. A separate module-local
consumer worker reads the event and prints the message.

Complete runnable source:
[examples/kafka-quick-start/app](https://github.com/polepos/poleposition/tree/main/examples/kafka-quick-start/app)

## Create the Project

Kafka is the focus, so start without database wiring:

```bash
polepos start kafka-quick-start --db none
cd kafka-quick-start
cp .env.example .env
uv sync --extra dev
```

## Add Kafka

```bash
polepos add integration kafka
uv sync --extra dev
```

The command creates:

```text
src/kafka_quick_start/integrations/kafka/
  __init__.py
  consumer.py
  factory.py
  producer.py
  schemas.py
  testing.py
```

Use these `.env` values for the quick start:

```env
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CLIENT_ID=kafka_quick_start
KAFKA_DEFAULT_TOPIC=greetings
KAFKA_GROUP_ID=greetings-demo
KAFKA_AUTO_OFFSET_RESET=earliest
KAFKA_ACKS=all
KAFKA_REQUEST_TIMEOUT_MS=40000
```

`KAFKA_AUTO_OFFSET_RESET=earliest` lets a fresh consumer group read messages
that were published before the worker started.

## Run Kafka

Use a local Kafka broker on `localhost:9092`. The full source scenario includes
a Docker Compose file with Kafka UI on `localhost:8081`.

Create the topic:

```bash
docker compose -f compose.kafka.yaml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 \
  --create \
  --if-not-exists \
  --topic greetings \
  --partitions 1 \
  --replication-factor 1
```

## Add the Module

```bash
polepos add module greetings --api-only
```

PolePosition creates:

```text
src/kafka_quick_start/modules/greetings/
  __init__.py
  router.py
  schemas.py
  services/
    __init__.py
    greetings_service.py
tests/integration/test_greetings.py
tests/unit/test_greetings_api_service.py
```

Reshape the generated files:

- `schemas.py` defines `GreetingRequest` and `GreetingResponse`
- `services/greetings_service.py` builds and publishes a `KafkaEvent`
- `router.py` exposes `POST /api/v1/greetings/send`
- `consumer.py` is a module-local worker that calls `consume_json_messages`

Run FastAPI:

```bash
uv run python -m kafka_quick_start.run
```

Run the worker:

```bash
uv run python -m kafka_quick_start.modules.greetings.consumer
```

Publish a message:

```bash
curl -X POST http://localhost:8000/api/v1/greetings/send \
  -H "Content-Type: application/json" \
  -d '{"recipient":"team","message":"Hello, PolePosition Kafka!"}'
```

Expected worker output:

```text
got: Hello, PolePosition Kafka!
```

## Test Shape

Use `InMemoryKafkaEventProducer` from the generated Kafka scaffold for fast unit
tests. Keep real broker tests in a separate Docker or Testcontainers flow.

The mapping from the Spring quick start is:

| Spring quick start | PolePosition equivalent |
| --- | --- |
| `KafkaTemplate` | generated `KafkaEventProducer` |
| `@KafkaListener` | module-local worker using `consume_json_messages` |
| `NewTopic` bean | explicit topic creation command or reviewed infra change |
| `application.yaml` Kafka settings | `.env` plus generated `settings.py` fields |
| `EmbeddedKafka` test | broker-free unit test with `InMemoryKafkaEventProducer` |

Validate the generated project contract:

```bash
polepos check
```

Full source scenario:
[examples/kafka-quick-start](https://github.com/polepos/poleposition/blob/main/examples/kafka-quick-start/README.md)
