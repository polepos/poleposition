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
| Lifecycle manifest | Growing | New projects include `.poleposition.toml` so package, database mode, module templates, CRUD feature options, and generated integrations do not depend only on inference. |
| `polepos add module` with `standard` | Growing | Strong differentiator; works well, but still depends on managed marker blocks. |
| `polepos add module` with `crud` | Growing | Database-backed CRUD skeleton with list/create/get/update/delete routes, repository/service layers, generated tests, and opt-in pagination, timestamps, soft delete, tenant scoping, and auth-required route protection. |
| `polepos add module` with `ai-prompt` | Growing | Good provider-agnostic foundation; adapters are scaffold-level boundaries for real provider integration. |
| `polepos add module` with `api-only` | Growing | Useful lightweight module archetype for routes that do not need model, repository, or database wiring. |
| `polepos add module` with `service-only` | Growing | Internal, database-backed module archetype (model, repository, service, and tests) that intentionally exposes no HTTP routes, for domain services, event handlers, background jobs, or integrations. |
| `polepos add auth` | Growing | Optional database-backed registration and token workflow with generated model, router, service, tests, and check coverage. |
| `polepos remove module` | Growing | Removes generated module scaffolds and managed wiring; supports `--wiring-only` for detaching managed references while preserving customized module files. |
| `polepos add integration kafka` | Growing | First messaging integration; producer, consumer factory, settings, env, and test double support are scaffolded. |
| `polepos add integration rabbitmq` | Growing | Second messaging integration; publisher, queue factory, settings, env, and test double support are scaffolded. |
| `polepos add integration redis` | Growing | Shared cache integration; async cache helper, settings, env, dependency, and test double support are scaffolded. |
| `polepos add integration rq` | Growing | Redis-backed background job queue helpers, worker factory, settings, env, dependency, and test double support are scaffolded. |
| `polepos check` | Stable foundation | Runs core checks for project identity, generated structure, Alembic config, managed markers, starter routing, added module lifecycle wiring, orphan remnants, opt-in integration wiring, JSON output, and safe marker fixes. |
| `polepos db ...` commands | Stable foundation | Good migration lifecycle wrapper around Alembic, including read-only status reporting. |
| `polepos upgrade` | Growing | Read-only project upgrade readiness report that summarizes CLI version, manifest state, integrations, modules, and check status. |
| `polepos completion` | Growing | Prints a `bash`, `zsh`, or `fish` completion script derived from the live command tree, completing commands, subcommands, flags, template/database values, integration names, and the current project's module names. |
| `polepos.data` runtime structures | Growing | Provides dependency-free in-memory structures such as caches, sorted containers, trie, graph, priority queue, and union-find. |
| Alembic migration support | Stable foundation | Generated projects are migration-first. |
| Docker and PostgreSQL workflow | Growing | Good local runtime story; Docker e2e exists as opt-in smoke coverage. |
| Auth foundation | Growing | Base auth helpers remain lightweight, and `polepos add auth` can now add the optional database-backed workflow. |
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
router wiring, and database-backed module model imports. `--trace` previews planned
removals and updates without mutating files. For AI prompt modules, the last
remaining AI prompt module removal also cleans up shared LLM scaffold settings
and files.

`--wiring-only` removes generated tests and managed router/model/export wiring
without deleting the module directory. It is useful when user code inside the
module has diverged but the generated lifecycle references still need cleanup.

It intentionally does not mutate database schema. Database-backed module
removal should be followed by an explicit Alembic revision only when the team
wants to drop or otherwise change the underlying table.

The command is conservative around custom layout drift: if it cannot recognize
managed wiring well enough to remove it cleanly, it stops before deleting the
module directory.

### External integrations

Kafka, RabbitMQ, Redis, and RQ are opt-in integrations rather than default
`polepos start` behavior. Kafka covers event streaming workflows, RabbitMQ covers
AMQP exchange/queue messaging, Redis covers shared cache helpers, and RQ covers
Redis-backed background job workers. Messaging consumers and job workers should
remain explicit runtime surfaces instead of being started automatically inside
the API process.

### Runtime data structures

`polepos.data` is a runtime namespace for application code. It is intentionally
separate from the internal `pole_position` CLI implementation package.

The first scope is dependency-free, in-memory structures that are useful inside
generated projects: caches, sorted containers, ordered sets, indexed priority
queues, tries, union-find, and small graph workflows. These structures are
process-local. Shared or persistent state should still live in Redis,
PostgreSQL, Kafka, RabbitMQ, Redis/RQ, or another reviewed infrastructure
dependency.

### Project checks

`polepos check` is now a stable lifecycle validation surface rather than a
template smoke check.

It currently validates:

- core project identity and generated structure
- Alembic migration setup
- PolePosition-managed markers
- starter status router wiring
- added module lifecycle wiring
- orphan generated remnants after manual module deletion
- Kafka, RabbitMQ, Redis, RQ, LLM, and auth workflow wiring

The default command is intentionally read-only and file-based. It is safe to run
from local development, CI, and agent workflows without requiring a running
database, message broker, LLM provider, or optional integration dependency.
Use `polepos check --json` when CI or agent tooling needs structured issue
codes, messages, and remediation text. Use `polepos check --fix` when safe
managed markers should be restored before validation.

### Auth foundation

The current auth layer covers:

- public vs protected endpoint boundaries
- current user resolution
- simple role-gated authorization
- optional generated registration and token login via `polepos add auth`

It is scoped away from:

- refresh tokens
- advanced permission systems

### AI prompt modules

The current `ai-prompt` template is intentionally provider-agnostic.
That is a strength, and it keeps provider adapters at scaffold level.

This is best understood as:

- a solid module architecture
- a useful orchestration pattern
- a starting point for real provider integration
