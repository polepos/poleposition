# Feature Status

This file describes the current maturity of PolePosition lifecycle features.

The goal is not to label features as simply "done" or "not done".
Instead, it clarifies whether a feature is:

- stable enough for normal use
- a strong foundation but still growing
- intentionally partial

## Status Levels

- `Stable foundation`: good default, broadly usable, expected to stay
- `Growing`: useful and real, with a documented current scope
- `Partial by design`: intentionally scoped down in the current product

## Current Status

| Area | Status | Notes |
|---|---|---|
| Project lifecycle CLI shape | Stable foundation | Product is organized around `start`, `add module`, `remove module`, `add integration`, `check`, and `db` workflows rather than a one-time template. |
| `polepos start` | Stable foundation | Core product entrypoint; generated project shape is now a major part of the product contract. |
| Template rendering | Stable foundation | Supporting mechanism for lifecycle workflows; placeholder replacement and template packaging are in good shape. |
| Generated FastAPI structure | Stable foundation | `auth`, `bootstrap`, `api`, `db`, `domain`, `integrations`, `modules` layout is now part of the product identity. |
| `polepos add module` with `standard` | Growing | Strong differentiator; works well, but still depends on managed marker blocks. |
| `polepos add module` with `ai-prompt` | Growing | Good provider-agnostic foundation; adapters are scaffold-level boundaries for real provider integration. |
| `polepos add module` with `api-only` | Growing | Useful lightweight module archetype for routes that do not need model, repository, or database wiring. |
| `polepos remove module` | Growing | Removes generated module scaffolds and managed wiring; intentionally stops when cleanup would require interpreting custom layout drift or deleting customized module files without `--force`. |
| `polepos add integration kafka` | Growing | First messaging integration; producer, consumer factory, settings, env, and test double support are scaffolded. |
| `polepos add integration rabbitmq` | Growing | Second messaging integration; publisher, queue factory, settings, env, and test double support are scaffolded. |
| `polepos check` | Stable foundation | Runs core checks for project identity, generated structure, Alembic config, managed markers, added module lifecycle wiring, and opt-in integration wiring. |
| `polepos db ...` commands | Stable foundation | Good migration lifecycle wrapper around Alembic. |
| Alembic migration support | Stable foundation | Generated projects are migration-first. |
| Docker and PostgreSQL workflow | Growing | Good local runtime story; Docker e2e exists as opt-in smoke coverage. |
| Auth foundation | Partial by design | Strong route-boundary pattern scoped to endpoint protection rather than full login/user management. |
| JSON logging support | Stable foundation | Works as a runtime format choice. |
| CORS support | Stable foundation | Settings-driven and production-aware. |
| Example scenarios | Growing | Scenario guides for onboarding and product understanding. |

## Important Clarifications

### Templates

Template files are part of how PolePosition ships project and module defaults.
They should not be treated as the product boundary: the CLI lifecycle around
starting, growing, checking, and migrating projects is the product shape.

### `add module`

This is one of the most important product surfaces.

It uses PolePosition-managed markers as its insertion contract.
That makes generated updates predictable while keeping surrounding project code
editable.

Generated modules keep workflow code in a module-local `services/` package
instead of a single root `service.py` file. That leaves room for additional
service classes as a module grows without pushing logic into global folders.

### `remove module`

This is the cleanup counterpart to `add module`.

It removes generated module directories, generated tests, module exports,
router wiring, and standard-module model imports. `--trace` previews planned
removals and updates without mutating files. For AI prompt modules, the last
remaining AI prompt module removal also cleans up shared LLM scaffold settings
and files.

It intentionally does not mutate database schema. Database-backed module
removal should be followed by an explicit Alembic revision only when the team
wants to drop or otherwise change the underlying table.

The command is conservative around custom layout drift: if it cannot recognize
managed wiring well enough to remove it cleanly, it stops before deleting the
module directory.

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

The command is intentionally read-only and file-based. It is safe to run from
local development, CI, and agent workflows without requiring a running
database, message broker, LLM provider, or optional integration dependency.

### Auth foundation

The current auth layer covers:

- public vs protected endpoint boundaries
- current user resolution
- simple role-gated authorization

It is scoped away from:

- login
- password storage
- refresh tokens
- database-backed users
- advanced permission systems

### AI prompt modules

The current `ai-prompt` template is intentionally provider-agnostic.
That is a strength, and it keeps provider adapters at scaffold level.

This is best understood as:

- a solid module architecture
- a useful orchestration pattern
- a starting point for real provider integration
