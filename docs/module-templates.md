# Module Templates

PolePosition module templates are starting points, not framework boundaries.
They create a consistent FastAPI module shape that you can edit for the real
domain.

## Template Summary

| Template | Command | Use when |
|---|---|---|
| `standard` | `polepos add module customers` | You need a database-backed REST module with model, repository, service, router, and tests. |
| `crud` | `polepos add module customers --template crud` | You want a fuller CRUD starting point with list, create, get, update, and delete routes. |
| `api-only` | `polepos add module webhooks --api-only` | You need routes and service code but no database model or repository. |
| `ai-prompt` | `polepos add module assistant --template ai-prompt` | You need an LLM-oriented module boundary and provider-agnostic adapter stubs. |
| `service-only` | `polepos add module notifications --service-only` | You need an internal, database-backed module (domain service, event handler, background job, integration) with no HTTP routes. |

All templates update:

- `src/<package>/modules/__init__.py`
- generated integration and unit tests
- `.poleposition.toml`

API-facing templates also update `src/<package>/api/router.py` to wire the
generated router. The `service-only` template is the exception: it exposes no
routes, so it never touches `api/router.py`.

Database-backed templates also update `src/<package>/db/models.py` so Alembic
can discover generated SQLAlchemy models.

## Generated Schema Contracts

Each template creates a `schemas.py` file with a small Pydantic contract. These
schemas are not meant to be the final domain model. They are the first working
API contract that lets the generated router, service, repository, and tests run
immediately after `polepos add module`.

Schema class names are derived from the module name. For example,
`polepos add module order_items` creates class names beginning with
`OrderItems`. PolePosition currently normalizes snake_case to PascalCase; it
does not singularize or pluralize module names.

| Template | Generated schema classes | Why these names are used |
|---|---|---|
| Starter `status` module | `StatusResponse` | The endpoint is read-only and does not accept a request body. |
| `standard` | `<ClassName>Create`, `<ClassName>Read` | The generated API supports collection list and create. `Create` is the incoming payload; `Read` is the response model returned from SQLAlchemy objects. |
| `crud` | `<ClassName>Create`, `<ClassName>Update`, `<ClassName>Read` | Full CRUD needs separate create and patch payloads plus a read response. |
| `api-only` | `<ClassName>Request`, `<ClassName>Response` | There is no database entity, so generic request and response names fit the lightweight route/service boundary. |
| `ai-prompt` | `<ClassName>PromptRequest`, `<ClassName>PromptResponse` | The module is prompt-oriented, so the schema names describe the LLM use case instead of a persisted resource. |
| `service-only` | None | The module exposes no HTTP routes, so it generates no request/response schemas. Its service methods take plain arguments and return SQLAlchemy models. |

The generated fields are intentionally small examples, not domain assumptions.
Database-backed templates start with `id` and `name` because that produces a
working model, request body, response body, repository, service, and pytest
flow. API-only templates use `name` and `message` for the same reason. AI prompt
templates use `prompt`, `topic`, `response`, `provider`, and `model` to show
the orchestration boundary.

After generation, replace those fields with the real domain contract. For
example, a `customers` module might keep `CustomerCreate` and `CustomerRead`,
but change the fields to:

```python
class CustomerCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
```

If your team prefers explicit API suffixes, you can rename the generated
classes, but treat that as a normal code refactor. For example,
`CustomerCreate` can become `CustomerCreateRequest` or
`CreateCustomerRequest`, and `CustomerRead` can become `CustomerResponse`.
Update every import and type reference in `router.py`, `services/`, generated
tests, and any custom code that imports the old class name.

Do not delete generated schema classes in isolation. In the `standard`
template, `router.py` imports `<ClassName>Create` and `<ClassName>Read`, and the
service imports `<ClassName>Create`. If only the schema classes are removed,
the app usually fails during import and pytest reports an `ImportError`. If the
class remains but a generated field such as `name` is removed, the app may
import but the generated service or tests can fail when they access
`payload.name` or assert `response["name"]`.

Safe schema customization means updating the whole module contract together:

- `schemas.py`
- `model.py` for database-backed modules
- `repository.py` for database-backed modules
- `services/<module>_service.py` or `services/<module>_crud_service.py`
- `router.py`
- generated unit and integration tests
- Alembic migrations when database fields change

`polepos check` and `pytest` validate different parts of this work.
`polepos check` validates the PolePosition lifecycle contract: files, manifest
metadata, managed markers, router wiring, model wiring, generated tests, and
integration wiring. It does not prove that a renamed schema class is still
imported everywhere or that a removed field is still compatible with service
logic. Run pytest after schema, router, service, or model edits:

```bash
polepos check
uv run pytest
```

## Standard Template

```bash
polepos add module customers
```

Generated module files:

```text
src/<package>/modules/customers/
  __init__.py
  model.py
  repository.py
  router.py
  schemas.py
  services/
    __init__.py
    customers_service.py
```

Generated tests:

```text
tests/integration/test_customers.py
tests/unit/test_customers_service.py
```

The standard template gives you collection endpoints and simple persistence.
Use it when the domain is not yet fully shaped but you know the module should
own a table.

After changing `model.py`, create and review a migration:

```bash
polepos db revision -m "add customers table"
polepos db upgrade
polepos check
```

## CRUD Template

```bash
polepos add module customers --template crud
```

Generated module files are similar to `standard`, but the service and tests use
CRUD-specific names:

```text
src/<package>/modules/customers/
  model.py
  repository.py
  router.py
  schemas.py
  services/
    customers_crud_service.py

tests/integration/test_customers_crud.py
tests/unit/test_customers_crud_service.py
```

Generated routes:

```text
GET    /api/v1/customers/
POST   /api/v1/customers/
GET    /api/v1/customers/{item_id}
PATCH  /api/v1/customers/{item_id}
DELETE /api/v1/customers/{item_id}
```

Use `crud` when a team wants a more complete REST skeleton immediately. The
generated fields are intentionally simple (`id` and `name`) so you can reshape
the model, schemas, repository, and service for the real aggregate.

### CRUD Feature Options

CRUD modules can opt into common enterprise API concerns at generation time:

```bash
polepos add module customers --template crud --pagination
polepos add module customers --template crud --timestamps
polepos add module customers --template crud --soft-delete
polepos add module customers --template crud --tenant-scoped
polepos add module customers --template crud --auth-required
```

The options can also be combined:

```bash
polepos add module customers --template crud \
  --pagination \
  --timestamps \
  --soft-delete \
  --tenant-scoped \
  --auth-required
```

These flags intentionally require `--template crud`. They are not accepted for
`standard`, `api-only`, or `ai-prompt` modules because the generated code
touches CRUD-specific router, repository, service, schema, and test contracts.

When a CRUD option is used, `.poleposition.toml` records the selected feature
set with the module template, for example:

```toml
[modules]
customers = "crud[pagination,timestamps,soft-delete,tenant-scoped,auth-required]"
```

`polepos check`, `polepos upgrade`, and `polepos remove module` use that value
to distinguish a pristine generated CRUD variant from hand-written changes. If
you hand-edit the manifest, keep the feature list aligned with the generated
files or `remove module` may conservatively report custom changes.

| Option | Generated behavior |
|---|---|
| `--pagination` | Adds `limit` and `offset` query parameters to the list route, adds `<ClassName>Page`, and returns `{items, total, limit, offset}` instead of a bare list. |
| `--timestamps` | Adds `created_at` and `updated_at` SQLAlchemy columns and response fields. The generated model uses a UTC timestamp helper and `onupdate` for updates. |
| `--soft-delete` | Adds a nullable `deleted_at` column. Delete routes mark the row as deleted instead of removing it, and generated list/get queries exclude deleted rows. |
| `--tenant-scoped` | Adds `tenant_id` to create/read schemas and the model. List/get/update/delete routes require a `tenant_id` query parameter and repository queries filter by tenant. |
| `--auth-required` | Protects all generated CRUD routes with `Depends(get_current_user)` at router level. Generated integration tests create a bearer token with the starter auth token helper. |

With all options enabled, the list route shape becomes:

```text
GET /api/v1/customers/?tenant_id=tenant-a&limit=100&offset=0
```

and the response shape is:

```json
{
  "items": [
    {
      "id": 1,
      "tenant_id": "tenant-a",
      "name": "Main Customer",
      "created_at": "2026-05-24T12:00:00Z",
      "updated_at": "2026-05-24T12:00:00Z",
      "deleted_at": null
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

The generated tenant scope is deliberately explicit: clients pass `tenant_id`
as an API parameter. Many enterprise systems later replace that with tenant
resolution from authenticated user claims, subdomains, API keys, or gateway
headers. When you make that change, update `router.py`, `services/`,
`repository.py`, and tests together.

`--auth-required` uses the starter token authentication helpers that already
exist in generated projects. It protects routes, but it does not generate
resource-level authorization rules, role policies, tenant membership checks, or
permission matrices. Add those rules in the service layer when the domain
requires them.

All database-affecting options require a reviewed migration before they exist in
the real database:

```bash
polepos db revision -m "add customers crud fields"
polepos db upgrade
polepos check
uv run pytest
```

## API-Only Template

```bash
polepos add module webhooks --api-only
polepos add module webhooks --template api-only
```

Generated module files:

```text
src/<package>/modules/webhooks/
  __init__.py
  router.py
  schemas.py
  services/
    __init__.py
    webhooks_service.py
```

API-only modules do not create:

- `model.py`
- `repository.py`
- `db/models.py` imports
- migrations

Use this template for webhooks, health-adjacent routes, proxies, callbacks, or
other API surfaces whose state lives elsewhere.

## Service-Only Template

```bash
polepos add module notifications --service-only
polepos add module notifications --template service-only
```

Generated module files:

```text
src/<package>/modules/notifications/
  __init__.py
  model.py
  repository.py
  services/
    __init__.py
    notifications_service.py
```

Service-only modules are internal: they own database state through a model and
repository, but they expose no HTTP routes. The template does not create:

- `router.py`
- `schemas.py`
- `api/router.py` wiring

Like the `standard` template, it does update `db/models.py` so Alembic can
discover the model, and the migration note applies after model changes. The
generated service exposes plain methods (for example `create_notifications`)
that take ordinary arguments instead of request schemas, so other modules,
lifecycle hooks, or background tasks can call it directly. The generated
integration test exercises the service against the database rather than an HTTP
client.

Use this template for domain services, event handlers, background processing,
or third-party integrations that should follow PolePosition module conventions
without becoming an API surface. `polepos check` understands that a service-only
module has no router and does not flag the missing route wiring.

## AI Prompt Template

```bash
polepos add module assistant --template ai-prompt
```

Generated module files:

```text
src/<package>/modules/assistant/
  __init__.py
  orchestrator.py
  prompts.py
  router.py
  schemas.py
  services/
    __init__.py
    assistant_service.py
```

When missing, the command also creates shared LLM integration stubs:

```text
src/<package>/integrations/llm/
  anthropic_client.py
  factory.py
  openai_client.py
  provider.py
  schemas.py
```

The generated LLM adapters are provider-agnostic stubs. Add real SDK calls only
after deciding which provider and deployment model the application should use.

## Choosing a Template

Choose `standard` when persistence matters but the API shape is still small.
Choose `crud` when the first useful version needs full item lifecycle routes.
Choose `api-only` when the route should not own database state. Choose
`service-only` when the module owns database state but should never expose HTTP
routes. Choose `ai-prompt` when orchestration and prompt boundaries are more
important than a database model.

Do not use generated module templates as final domain design. Treat them as a
consistent first commit, then refine names, validation, relationships,
transactions, authorization, and tests for the real use case.

## Validation

Run:

```bash
polepos check
```

`check` uses `.poleposition.toml` first, then structural detection for older
projects. If a generated module directory was removed manually, use:

```bash
polepos remove module <name>
```

to clean managed router, model, export, and test references. Use
`--wiring-only` when customized module files should be preserved while
PolePosition-managed references are detached.
