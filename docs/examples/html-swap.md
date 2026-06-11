# HTML Swap Example

This scenario shows how a generated module can be reshaped into a focused HTML
transformation endpoint backed by PostgreSQL history.

The target endpoint:

```text
POST /api/v1/html/swap
```

The endpoint accepts HTML, replaces configured links, stores the operation, and
returns the updated HTML.

## Create the Project

```bash
polepos start html-tools
cd html-tools
cp .env.example .env
uv sync --extra dev
polepos db upgrade
uv run python -m html_tools.run
```

For PostgreSQL-backed local development, point `DATABASE_URL` at your database:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/html_tools
```

## Generate the Module

```bash
polepos add module html --api-only
```

PolePosition creates:

```text
src/html_tools/modules/html/
  __init__.py
  router.py
  schemas.py
  services/
    __init__.py
    html_service.py
tests/integration/test_html.py
tests/unit/test_html_api_service.py
```

## Reshape the Module

Keep the generated module boundary, then reshape the internals for the real
workflow:

- `schemas.py` defines the HTML swap request contract
- `services/html_service.py` parses HTML and performs replacements
- `router.py` exposes `POST /api/v1/html/swap`
- add `model.py` when swap history becomes part of the contract
- add `repository.py` to persist completed operations

Use a parser dependency instead of string replacement:

```bash
uv add beautifulsoup4
```

## Request Shape

```json
{
  "html": "<html><body><a href=\"https://old.example.com/pricing\">Pricing</a></body></html>",
  "replacements": [
    {
      "from_url": "https://old.example.com/pricing",
      "to_url": "https://new.example.com/pricing"
    }
  ]
}
```

Return raw HTML when the consumer expects HTML directly. Return JSON only when
the caller needs metadata such as updated link count or stored operation ID.

Full source scenario:
[examples/html-swap](https://github.com/polepos/poleposition/blob/main/examples/html-swap/README.md)
