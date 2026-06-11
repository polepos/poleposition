# OpenAI Prompt Example

This tutorial turns the `ai-prompt` module template into a working OpenAI-backed
prompt endpoint.

The target endpoint:

```text
POST /api/v1/assistant/respond
```

The implementation uses the OpenAI Responses API pattern shown in the official
[OpenAI developer quickstart](https://platform.openai.com/docs/quickstart?api-mode=responses&lang=python)
and [Responses API reference](https://platform.openai.com/docs/api-reference/responses).

Complete runnable source:
[examples/openai-prompt/app](https://github.com/polepos/poleposition/tree/main/examples/openai-prompt/app)

## Create the Project

```bash
polepos start openai-prompt --db none
cd openai-prompt
cp .env.example .env
uv sync --extra dev
```

## Add the AI Prompt Module

```bash
polepos add module assistant --template ai-prompt
uv add openai
uv sync --extra dev
```

The module template creates:

```text
src/openai_prompt/modules/assistant/
  orchestrator.py
  prompts.py
  router.py
  schemas.py
  services/assistant_service.py

src/openai_prompt/integrations/llm/
  factory.py
  openai_client.py
  provider.py
  schemas.py
```

Use these `.env` values:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.4-mini
LLM_API_KEY=your_openai_api_key
LLM_BASE_URL=
LLM_TIMEOUT_SECONDS=30.0
LLM_TEMPERATURE=0.2
# LLM_MAX_TOKENS=
```

## Implement the Adapter

The generated `openai_client.py` is intentionally a stub. Replace
`OpenAIProvider.generate_text()` with a Responses API call:

```python
client = OpenAI(
    api_key=self.api_key,
    base_url=self.base_url or None,
    timeout=self.timeout_seconds,
)
request = {
    "model": self.model,
    "instructions": system_prompt,
    "input": user_prompt,
    "temperature": self.temperature,
}
if self.max_tokens is not None:
    request["max_output_tokens"] = self.max_tokens

response = client.responses.create(**request)
return LLMTextResult(
    text=response.output_text,
    provider="openai",
    model=self.model,
)
```

Why this shape:

- provider SDK code stays under `integrations/llm`
- `prompts.py` owns system prompts
- `orchestrator.py` combines system prompt and user prompt
- `router.py` remains FastAPI-native and small
- unit tests can inject a stub provider and avoid live API calls

Run the app:

```bash
uv run python -m openai_prompt.run
```

Send a prompt:

```bash
curl -X POST http://localhost:8000/api/v1/assistant/respond \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "support_reply",
    "prompt": "A customer says their invoice total looks wrong. Draft a reply."
  }'
```

## Test Shape

Keep live OpenAI calls out of the default unit suite. Test the module by passing
a stub provider to `AssistantOrchestrator`, returning `LLMTextResult`, and
asserting that:

- the expected system prompt was used
- the user's prompt was passed through
- provider/model/response fields were mapped into the API response

Validate:

```bash
uv run pytest
polepos check
```

Full source scenario:
[examples/openai-prompt](https://github.com/polepos/poleposition/blob/main/examples/openai-prompt/README.md)
