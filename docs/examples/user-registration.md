# User Registration REST API Example

This guide shows a realistic PolePosition workflow for a developer who wants to
build a user registration REST API.

The target endpoint:

```text
POST /api/v1/users/register
```

The endpoint accepts an email, password, and optional full name. It stores only
a password hash and returns a public user representation.

## 1. Create the Project

```bash
polepos start account-api
cd account-api
cp .env.example .env
uv sync
polepos db upgrade
uv run python -m account_api.run
```

The project starts with the generated FastAPI app, database foundation, Alembic
migrations, auth foundation, and `status` module.

For this guide, keep the default SQLite database while developing locally. When
you are ready to use PostgreSQL, update `DATABASE_URL` in `.env` and run the
same migration commands.

## 2. Add Domain Dependencies

This example uses `EmailStr` validation and Argon2 password hashing:

```bash
uv add email-validator "pwdlib[argon2]"
```

`email-validator` enables Pydantic email validation. `pwdlib[argon2]` provides
modern password hashing.

## 3. Generate the Users Module

```bash
polepos add module users
```

PolePosition creates:

```text
src/account_api/modules/users/
  __init__.py
  model.py
  repository.py
  router.py
  schemas.py
  services/
    __init__.py
    users_service.py
tests/integration/test_users.py
tests/unit/test_users_service.py
```

It also updates:

```text
src/account_api/api/router.py
src/account_api/db/models.py
src/account_api/modules/__init__.py
```

The generated class name for a `users` module is `Users`. In a real domain,
the entity is singular, so the next steps intentionally rename the model and
schemas to `User`, `UserCreate`, and `UserRead`.

## 4. Create `security.py`

Create:

```text
src/account_api/modules/users/security.py
```

Add:

```python
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, password_hash_value: str) -> bool:
    return password_hash.verify(password, password_hash_value)
```

Registration uses `hash_password`. `verify_password` is included because the
same module will usually grow a login endpoint later.

## 5. Replace `model.py`

Replace:

```text
src/account_api/modules/users/model.py
```

with:

```python
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from account_api.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(512))
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
```

Important details:

- `email` is unique and indexed because registration must reject duplicates.
- `hashed_password` stores the hash, never the raw password.
- `created_at` is set in application code for a simple first version.

## 6. Replace `schemas.py`

Replace:

```text
src/account_api/modules/users/schemas.py
```

with:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class UserCreate(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)
    full_name: str | None = Field(default=None, min_length=2, max_length=120)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime
```

`UserCreate` accepts a password. `UserRead` does not expose either `password`
or `hashed_password`.

## 7. Replace `repository.py`

Replace:

```text
src/account_api/modules/users/repository.py
```

with:

```python
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from account_api.modules.users.model import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.db.scalar(statement)

    def create(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str | None,
    ) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
        )
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        self.db.refresh(user)
        return user
```

The service checks for duplicate emails before insert. The repository still
handles `IntegrityError` because the database unique constraint is the final
source of truth.

## 8. Replace `services/users_service.py`

Replace:

```text
src/account_api/modules/users/services/users_service.py
```

with:

```python
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from account_api.bootstrap.logging import get_logger
from account_api.domain.exceptions import DomainError
from account_api.modules.users.model import User
from account_api.modules.users.repository import UserRepository
from account_api.modules.users.schemas import UserCreate
from account_api.modules.users.security import hash_password


logger = get_logger(__name__)


class UserService:
    def __init__(self, db: Session) -> None:
        self.repository = UserRepository(db)

    def register_user(self, payload: UserCreate) -> User:
        email = str(payload.email).lower()

        if self.repository.get_by_email(email) is not None:
            raise DomainError("User email is already registered.")

        logger.info("Registering user", extra={"email": email})

        try:
            return self.repository.create(
                email=email,
                hashed_password=hash_password(payload.password.get_secret_value()),
                full_name=payload.full_name,
            )
        except IntegrityError as exc:
            raise DomainError("User email is already registered.") from exc
```

The service owns business rules:

- normalize email
- reject duplicate registrations
- hash the password
- avoid logging the raw password

Replace:

```text
src/account_api/modules/users/services/__init__.py
```

with:

```python
from account_api.modules.users.services.users_service import (
    UserService,
)

__all__ = ["UserService"]
```

## 9. Replace `router.py`

Replace:

```text
src/account_api/modules/users/router.py
```

with:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from account_api.api.deps import db_session
from account_api.modules.users.schemas import UserCreate, UserRead
from account_api.modules.users.services import UserService


router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: UserCreate,
    db: Session = Depends(db_session),
) -> UserRead:
    return UserService(db).register_user(payload)
```

PolePosition already wired the module router into:

```text
src/account_api/api/router.py
```

So the final route is:

```text
POST /api/v1/users/register
```

## 10. Replace the Integration Test

Replace:

```text
tests/integration/test_users.py
```

with:

```python
from fastapi.testclient import TestClient


def test_register_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/users/register",
        json={
            "email": "Driver@Example.com",
            "password": "correct-horse-battery",
            "full_name": "Test Driver",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "driver@example.com"
    assert payload["full_name"] == "Test Driver"
    assert payload["is_active"] is True
    assert "password" not in payload
    assert "hashed_password" not in payload


def test_register_user_rejects_duplicate_email(client: TestClient) -> None:
    payload = {
        "email": "driver@example.com",
        "password": "correct-horse-battery",
        "full_name": "Test Driver",
    }

    first_response = client.post("/api/v1/users/register", json=payload)
    second_response = client.post("/api/v1/users/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert second_response.json() == {
        "detail": "User email is already registered.",
    }
```

## 11. Replace the Unit Test

Replace:

```text
tests/unit/test_users_service.py
```

with:

```python
from unittest.mock import Mock

from account_api.modules.users.schemas import UserCreate
from account_api.modules.users.services import UserService


def test_register_user_hashes_password_and_creates_user() -> None:
    service = UserService(db=Mock())
    service.repository = Mock()
    service.repository.get_by_email.return_value = None

    payload = UserCreate(
        email="Driver@Example.com",
        password="correct-horse-battery",
        full_name="Test Driver",
    )

    service.register_user(payload)

    service.repository.get_by_email.assert_called_once_with("driver@example.com")
    create_kwargs = service.repository.create.call_args.kwargs
    assert create_kwargs["email"] == "driver@example.com"
    assert create_kwargs["full_name"] == "Test Driver"
    assert create_kwargs["hashed_password"] != "correct-horse-battery"
    assert create_kwargs["hashed_password"].startswith("$argon2")
```

## 12. Run Checks and Tests

```bash
polepos check
uv run pytest
```

`polepos check` validates the generated project contract. `pytest` validates
the behavior you added to the users module.

## 13. Generate and Apply the Migration

```bash
polepos db revision -m "create users table"
```

Open the generated file:

```text
migrations/versions/<revision>_create_users_table.py
```

The revision id is different in every project, but the migration should contain
operations similar to:

```python
op.create_table(
    "users",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("email", sa.String(length=255), nullable=False),
    sa.Column("hashed_password", sa.String(length=512), nullable=False),
    sa.Column("full_name", sa.String(length=120), nullable=True),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id"),
)
op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
```

Then apply it:

```bash
polepos db upgrade
```

## 14. Run the API

```bash
uv run python -m account_api.run
```

Create a user:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "driver@example.com",
    "password": "correct-horse-battery",
    "full_name": "Test Driver"
  }'
```

Expected response shape:

```json
{
  "id": 1,
  "email": "driver@example.com",
  "full_name": "Test Driver",
  "is_active": true,
  "created_at": "2026-05-02T12:00:00Z"
}
```

No password or password hash is returned.

## What You Built

At the end of this flow, the project has:

- a generated FastAPI project structure
- a domain-specific `users` module
- `POST /api/v1/users/register`
- email validation
- password hashing
- duplicate email protection
- integration and unit tests
- Alembic-managed database schema

This is the intended PolePosition workflow: generate the shape, keep the app
FastAPI-native, then refine module files around the real domain.

## Production Follow-Up

Before treating this as a complete account system, add:

- login and token issuance
- email verification
- password reset
- rate limiting for registration and login endpoints
- audit logging for account lifecycle events
- production-specific password policy
- database-backed uniqueness checks tested against PostgreSQL
