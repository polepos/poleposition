# Feature Status

This file describes the current maturity of PolePosition lifecycle features.

The goal is not to label features as simply "done" or "not done".
Instead, it clarifies whether a feature is:

- stable enough for normal use
- a strong foundation but still growing
- intentionally partial

## Status Levels

- `Stable foundation`: good default, broadly usable, expected to stay
- `Growing`: useful and real, but likely to evolve
- `Partial by design`: intentionally scoped down for now

## Current Status

| Area | Status | Notes |
|---|---|---|
| Project lifecycle CLI shape | Stable foundation | Product is organized around `start`, `add module`, `add integration`, `check`, and `db` workflows rather than a one-time template. |
| `polepos start` | Stable foundation | Core product entrypoint; generated project shape is now a major part of the product contract. |
| Template rendering | Stable foundation | Supporting mechanism for lifecycle workflows; placeholder replacement and template packaging are in good shape. |
| Generated FastAPI structure | Stable foundation | `auth`, `bootstrap`, `api`, `db`, `domain`, `integrations`, `modules` layout is now part of the product identity. |
| `polepos add module` with `standard` | Growing | Strong differentiator; works well, but still depends on managed marker blocks. |
| `polepos add module` with `ai-prompt` | Growing | Good provider-agnostic foundation; adapters are scaffold-level, not full provider integrations yet. |
| `polepos add module` with `api-only` | Growing | Useful lightweight module archetype for routes that do not need model, repository, or database wiring. |
| `polepos add integration kafka` | Growing | First messaging integration; producer, consumer factory, settings, env, and test double support are scaffolded. |
| `polepos add integration rabbitmq` | Growing | Second messaging integration; publisher, queue factory, settings, env, and test double support are scaffolded. |
| `polepos check` | Stable foundation | Runs core checks for project identity, generated structure, Alembic config, managed markers, added module lifecycle wiring, and opt-in integration wiring. |
| `polepos db ...` commands | Stable foundation | Good migration lifecycle wrapper around Alembic. |
| Alembic migration support | Stable foundation | Generated projects are migration-first. |
| Docker and PostgreSQL workflow | Growing | Good local runtime story; Docker e2e exists as opt-in smoke coverage. |
| Auth foundation | Partial by design | Strong route-boundary pattern; not yet a complete login/user management system. |
| JSON logging support | Stable foundation | Works as a runtime format choice; deeper request-context enrichment can still improve. |
| CORS support | Stable foundation | Settings-driven and production-aware. |
| Example scenarios | Growing | Good for onboarding and product understanding; should expand over time. |

## Important Clarifications

### Templates

Template files are part of how PolePosition ships project and module defaults.
They should not be treated as the product boundary: the CLI lifecycle around
starting, growing, checking, and migrating projects is the product shape.

### `add module`

This is one of the most important product surfaces.

It is already useful, but it still assumes PolePosition-managed markers remain in place.
That means it is powerful, but not fully free-form.

Near-term improvements should continue focusing on ergonomics rather than
expanding the top-level command surface: clearer guidance in command output,
additional module archetypes, and scoped generation options.

### Messaging integrations

Kafka and RabbitMQ are opt-in messaging integrations rather than default
`polepos start` behavior. Kafka covers event streaming workflows; RabbitMQ covers
AMQP exchange/queue messaging. Both should remain explicit runtime or worker
surfaces instead of being started automatically inside the API process.

### Project checks

`polepos check` is now a stable lifecycle validation surface rather than a
template smoke check.

It currently validates:

- core project identity and generated structure
- Alembic migration setup
- PolePosition-managed markers
- added module lifecycle wiring
- Kafka, RabbitMQ, and LLM opt-in integration wiring

The command is intentionally read-only and file-based. It should remain safe to
run from local development, CI, and agent workflows without requiring a running
database, message broker, LLM provider, or optional integration dependency.

Future improvements should focus on better output and automation surfaces such
as `--json`, issue codes, severity levels, and possibly a limited `--fix` mode
for safe marker restoration.

### Auth foundation

The current auth layer solves:

- public vs protected endpoint boundaries
- current user resolution
- simple role-gated authorization

It does not yet solve:

- login
- password storage
- refresh tokens
- database-backed users
- advanced permission systems

### AI prompt modules

The current `ai-prompt` template is intentionally provider-agnostic.
That is a strength, but it also means provider adapters are not yet full out-of-the-box integrations.

This is best understood as:

- a solid module architecture
- a useful orchestration pattern
- a starting point for real provider integration

## Recommended Interpretation For Contributors

When deciding how to change the repo:

- preserve `Stable foundation` areas carefully
- improve `Growing` areas without overcomplicating them
- avoid presenting `Partial by design` areas as complete systems

That balance is important for keeping product messaging honest while still building a strong platform.
