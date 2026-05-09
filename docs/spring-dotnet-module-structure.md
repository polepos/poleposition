# Module Structure for Spring Boot and .NET Teams

This guide explains PolePosition's module structure for readers who may not
know PolePosition or FastAPI yet.

The short version:

PolePosition gives FastAPI projects a familiar enterprise shape without turning
FastAPI into Spring Boot or ASP.NET Core. A module is a small feature boundary:
routes, schemas, service logic, repository code, and optional database model
live together.

## Mental Model

If you come from Spring Boot, think of a PolePosition module as a feature
package that contains a controller, service, repository, DTOs, and entity.

If you come from ASP.NET Core, think of a PolePosition module as a feature
folder with endpoints or a controller, request and response models, service
logic, repository code, and an EF Core-style entity.

PolePosition keeps the same idea but uses FastAPI and SQLAlchemy names.

| Concept | Spring Boot | ASP.NET Core | PolePosition / FastAPI |
|---|---|---|---|
| Web endpoint group | `@RestController` | Controller or Minimal API group | `router.py` with `APIRouter` |
| Endpoint declaration | `@GetMapping`, `@PostMapping` | `[HttpGet]`, `MapGet`, `MapPost` | `@router.get`, `@router.post` |
| Request and response types | DTOs or records | DTOs, records, request models | `schemas.py` with Pydantic models |
| Business logic | `@Service` | service class | `services/<module>_service.py` |
| Persistence boundary | `@Repository` | repository or DbContext wrapper | `repository.py` |
| Database model | JPA `@Entity` | EF Core entity | `model.py` with SQLAlchemy model |
| Database migrations | Flyway or Liquibase | EF Core migrations | Alembic migrations |
| App route composition | component scan plus MVC config | `Program.cs` route mapping | `api/router.py` includes module routers |

## Java and FastAPI Vocabulary

This table is intentionally more detailed for Spring Boot and Java readers.

| Java / Spring Boot | Python / FastAPI / PolePosition |
|---|---|
| `@Entity` | SQLAlchemy model class in `model.py` |
| `@Table(name = "...")` | `__tablename__ = "..."` in a SQLAlchemy model |
| JPA field annotations such as `@Column` | SQLAlchemy `mapped_column(...)` |
| DTO, record, request object | Pydantic model in `schemas.py` |
| `@Valid` | FastAPI automatically validates Pydantic request models |
| Bean Validation such as `@NotBlank`, `@Size`, `@Email` | Pydantic field types and `Field(...)` constraints |
| Validation errors | FastAPI `422` validation responses |
| Lombok `@Data` | Pydantic models and normal Python classes remove most boilerplate |
| Lombok `@Builder` | Pydantic model construction, `.model_validate(...)`, and `.model_copy(...)` |
| `@RestController` | `router.py` with `APIRouter` |
| `@GetMapping`, `@PostMapping` | `@router.get`, `@router.post` |
| `@Service` | module-local service class under `services/` |
| `@Repository` | `repository.py` repository class |
| `@Transactional` | explicit SQLAlchemy session, commit, rollback, and transaction handling |
| `application.yml` or `application.properties` | `.env` plus `settings.py` |
| Spring profiles | `APP_ENV` and settings-driven environment behavior |
| Flyway or Liquibase migration | Alembic revision under `migrations/versions/` |

For example, Java Bean Validation:

```java
public record CustomerCreate(
    @NotBlank
    @Size(max = 120)
    String name
) {}
```

maps naturally to a Pydantic schema:

```python
from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
```

When this schema is used as a FastAPI endpoint parameter, FastAPI validates the
request body before your service logic runs.

## .NET and FastAPI Vocabulary

This table is intentionally more detailed for ASP.NET Core and EF Core readers.

| ASP.NET Core / .NET | Python / FastAPI / PolePosition |
|---|---|
| Controller class | `router.py` with `APIRouter` |
| Minimal API route group | module `router.py` included with a prefix |
| `[HttpGet]`, `[HttpPost]`, `[HttpPatch]` | `@router.get`, `@router.post`, `@router.patch` |
| Route attributes such as `[Route("api/customers")]` | `include_router(..., prefix="/customers")` |
| Request DTO or command record | Pydantic request model in `schemas.py` |
| Response DTO or view model | Pydantic response model in `schemas.py` |
| Data annotations such as `[Required]`, `[StringLength]`, `[EmailAddress]` | Pydantic field types and `Field(...)` constraints |
| Model binding | FastAPI parameter and request body parsing |
| ModelState validation | FastAPI automatic validation responses |
| `IServiceCollection` registration | direct imports, dependency functions, and explicit wiring |
| Service class | module-local service class under `services/` |
| Repository class | `repository.py` repository class |
| EF Core entity | SQLAlchemy model class in `model.py` |
| `DbSet<Customer>` | SQLAlchemy model plus repository queries |
| `DbContext` | SQLAlchemy `Session` and session factory |
| EF Core migrations | Alembic revisions under `migrations/versions/` |
| `appsettings.json` | `.env` plus `settings.py` |
| ASP.NET Core environments | `APP_ENV` and settings-driven environment behavior |
| Middleware pipeline | FastAPI middleware in `bootstrap/middleware.py` |
| Exception filters or problem details middleware | exception handlers in `bootstrap/errors.py` |

For example, a .NET request record with data annotations:

```csharp
public sealed record CustomerCreate(
    [Required]
    [StringLength(120, MinimumLength = 1)]
    string Name
);
```

maps naturally to a Pydantic schema:

```python
from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
```

ASP.NET Core model binding and validation usually happen before the controller
action runs. FastAPI behaves similarly for Pydantic request models: invalid
request bodies receive validation responses before your service logic runs.

## Generated Project Shape

A generated PolePosition app uses this shape:

```text
src/<package>/
  app.py
  run.py
  api/
    router.py
  db/
    base.py
    models.py
    session.py
  modules/
    status/
```

The important folder is `modules/`. Each domain feature belongs there.

## Standard Module Shape

When you run:

```bash
polepos add module customers
```

PolePosition creates:

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
tests/integration/test_customers.py
tests/unit/test_customers_service.py
```

It also updates:

```text
src/<package>/api/router.py
src/<package>/db/models.py
src/<package>/modules/__init__.py
```

That means the module is generated, registered with the API router, and wired
for Alembic model discovery.

## File Responsibilities

### `router.py`

This is closest to a Spring `@RestController` or an ASP.NET Core controller.
It owns HTTP route declarations.

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_customers():
    ...
```

In FastAPI, route decorators attach endpoints to an `APIRouter`. They do not
hide the route; they define it directly in normal Python code.

### `schemas.py`

This is closest to DTOs, request models, response models, or records.
PolePosition uses Pydantic models here.

```python
from pydantic import BaseModel


class CustomerCreate(BaseModel):
    name: str


class CustomerRead(BaseModel):
    id: int
    name: str
```

### `services/<module>_service.py`

This is the business workflow boundary. Keep domain decisions here instead of
putting all logic directly in the router.

```python
class CustomerService:
    def create_customer(self, payload: CustomerCreate):
        ...
```

### `repository.py`

This is the persistence boundary. It uses SQLAlchemy sessions and queries.

```python
class CustomerRepository:
    def list(self):
        ...
```

### `model.py`

This is the SQLAlchemy database model. It is closest to a JPA entity or EF Core
entity.

```python
class Customer(Base):
    __tablename__ = "customers"
```

Schema changes should flow through Alembic migrations, not application startup.

## How Router Wiring Works

`polepos add module customers` creates the module router and registers it in
`src/<package>/api/router.py`:

```python
from <package>.modules.customers.router import router as customers_router

api_router.include_router(customers_router, prefix="/customers", tags=["customers"])
```

This registration happens once per module.

After that, if you add more endpoints inside:

```text
src/<package>/modules/customers/router.py
```

you do not need to edit the main router again.

For example:

```python
@router.get("/{customer_id}")
def get_customer(customer_id: int):
    ...


@router.patch("/{customer_id}")
def update_customer(customer_id: int):
    ...
```

Those endpoints are automatically part of the already-included customers
router.

You only need another main router registration when you create another
`APIRouter`, another module, or a separate router file manually.

## How This Differs From Spring Component Scanning

Spring Boot often discovers controllers and services through annotations and
component scanning.

PolePosition does not rely on hidden component scanning. It keeps the FastAPI
composition explicit:

- module endpoints use `@router.get`, `@router.post`, and similar decorators
- the module router is included once in `api/router.py`
- database models are imported through `db/models.py` for Alembic metadata

This makes the project easier for humans and coding agents to inspect. The
route tree is normal Python code, not hidden framework state.

## How This Differs From ASP.NET Core `Program.cs`

ASP.NET Core often maps controllers or endpoint groups in `Program.cs`.

PolePosition uses `api/router.py` for that composition role. It is the central
API router file:

```text
src/<package>/api/router.py
```

The FastAPI app includes that API router in `app.py`, and each module router is
included under it.

## API-Only Modules

If a feature does not need a database model or repository, use:

```bash
polepos add module webhooks --api-only
```

This creates:

```text
src/<package>/modules/webhooks/
  __init__.py
  router.py
  schemas.py
  services/
    __init__.py
    webhooks_service.py
```

Use this for callbacks, health-adjacent endpoints, transformation endpoints, or
thin orchestration surfaces that do not need database tables yet.

## AI Prompt Modules

If a feature is an LLM prompt workflow, use:

```bash
polepos add module assistant --template ai-prompt
```

This creates a module with:

```text
orchestrator.py
prompts.py
router.py
schemas.py
services/
  __init__.py
  assistant_service.py
```

It also creates shared `integrations/llm` adapter stubs when missing.

## What To Edit After Generation

For a real domain, expect to edit:

- `model.py`: database fields and table shape
- `schemas.py`: request and response contracts
- `services/<module>_service.py`: business rules and workflow orchestration
- `repository.py`: queries and persistence behavior
- `router.py`: endpoint paths and HTTP behavior
- generated tests: examples of expected behavior

The generated module is a strong starting point, not the final business system.

## What Not To Do

Avoid these patterns:

- do not put all features in one global `services/` folder
- do keep service classes inside the owning module's `services/` package
- do not create tables during FastAPI startup
- do not bypass Alembic for schema changes
- do not manually recreate module boilerplate when `polepos add module` fits
- do not remove PolePosition-managed markers unless you intentionally opt out

## Lifecycle Flow

Use this flow when growing a REST API:

```bash
polepos add module customers
# edit model.py, schemas.py, services/customers_service.py, repository.py, router.py
polepos check
polepos db revision -m "add customers table"
polepos db upgrade
uv run pytest
```

For coding agents and LLMs, the rule is:

When the user asks for a new domain feature, prefer generating a PolePosition
module first, then reshape that module for the real domain.
