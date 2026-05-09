# LLM Integration

LLM scaffolding is generated through the AI prompt module template:

```bash
polepos add module assistant --template ai-prompt
```

The command creates a module such as:

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

It also creates shared LLM adapter files when missing:

```text
src/<package>/integrations/llm/
  __init__.py
  anthropic_client.py
  factory.py
  openai_client.py
  provider.py
  schemas.py
```

## Settings

Review the LLM values in `.env`:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.4-mini
LLM_API_KEY=
LLM_BASE_URL=
LLM_TIMEOUT_SECONDS=30.0
LLM_TEMPERATURE=0.2
# LLM_MAX_TOKENS=
```

Set `LLM_API_KEY` before calling generated endpoints against a real provider.

## Provider Boundary

The generated provider adapters are stubs. They define where provider-specific
SDK calls should live without making the base scaffold depend on a provider SDK.

Install the SDK you choose in the generated project, then implement the adapter
method in the matching provider file.

## Module Boundary

Use the generated files this way:

- `prompts.py`: prompt construction
- `orchestrator.py`: provider call orchestration
- `services/assistant_service.py`: application workflow boundary
- `router.py`: FastAPI endpoint contract
- `schemas.py`: request and response models

## Testing

Generated tests patch the provider boundary so tests do not call an external
LLM provider.

## Validate

```bash
polepos check
```

The check command validates LLM files, settings, and env values without
contacting a provider.
