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
LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=
LLM_BASE_URL=
LLM_TIMEOUT_SECONDS=30.0
LLM_TEMPERATURE=0.2
# LLM_MAX_TOKENS=
```

The scaffold ships provider-agnostic, so `LLM_PROVIDER` and `LLM_MODEL` are empty
by default. Set `LLM_PROVIDER` to a supported adapter (`openai` or `anthropic`)
and `LLM_MODEL` to a model id from that provider before calling the factory.
Set `LLM_API_KEY` before calling generated endpoints against a real provider.
The key should remain active in `.env.example`, even when its value is empty.
`LLM_MAX_TOKENS` is optional and may remain commented until needed.

## Provider Boundary

The generated provider adapters are stubs. They define where provider-specific
SDK calls should live without making the base scaffold depend on a provider SDK.

Install the SDK you choose in the generated project, then implement the adapter
method in the matching provider file.

For a complete OpenAI adapter walkthrough, see the
[OpenAI Prompt example](../examples/openai-prompt.md).

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
contacting a provider. It treats commented required values such as
`# LLM_PROVIDER=openai` as missing, while allowing optional examples such as
`# LLM_MAX_TOKENS=`.
