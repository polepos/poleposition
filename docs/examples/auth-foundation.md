# Auth Foundation Example

This scenario shows how to use the authentication foundation that comes with a
generated PolePosition project.

The generated project includes:

- public `GET /api/v1/status`
- JWT token helpers
- `get_current_user`
- `require_roles(...)`

It does not generate a default protected profile route. Protected routes should
belong to the real module that needs them.

## Create the Project

```bash
polepos start secure-api
cd secure-api
cp .env.example .env
uv sync --extra dev
polepos db upgrade
```

## Add an API Module

Use an API-only module for a small auth boundary example:

```bash
polepos add module account --api-only
```

Then update `src/secure_api/modules/account/router.py` to use the generated auth
dependencies:

```python
from fastapi import APIRouter, Depends

from secure_api.api.deps import get_current_user, require_roles
from secure_api.auth.schemas import AuthenticatedUser


router = APIRouter()


@router.get("/me")
def read_account(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, object]:
    return current_user.model_dump()


@router.get("/admin-preview")
def read_admin_preview(
    current_user: AuthenticatedUser = Depends(require_roles("admin")),
) -> dict[str, object]:
    return current_user.model_dump()
```

Run the project:

```bash
uv run python -m secure_api.run
```

## Generate a Local Token

The foundation does not ship with a full login system yet, so local testing can
mint a token directly from the generated helper:

```bash
TOKEN=$(uv run python -c 'from secure_api.auth.token import create_access_token; print(create_access_token(subject="user-1", email="user@example.com", roles=["member"]))')
```

For an admin role:

```bash
ADMIN_TOKEN=$(uv run python -c 'from secure_api.auth.token import create_access_token; print(create_access_token(subject="admin-1", email="admin@example.com", roles=["admin", "member"]))')
```

## Exercise the Boundaries

Public endpoint:

```bash
curl http://127.0.0.1:8000/api/v1/status
```

Protected endpoint:

```bash
curl http://127.0.0.1:8000/api/v1/account/me \
  -H "Authorization: Bearer $TOKEN"
```

Admin endpoint:

```bash
curl http://127.0.0.1:8000/api/v1/account/admin-preview \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

The important boundary is simple:

- authentication answers who is calling
- authorization answers whether that caller can access the route

Full source scenario:
[examples/auth-foundation](https://github.com/polepos/poleposition/blob/main/examples/auth-foundation/README.md)
