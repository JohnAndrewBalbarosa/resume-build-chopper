# `llm/` — Provider-Agnostic LLM Layer

One interface, many providers. Pipeline stages depend only on the `LLMProvider` ABC; choosing a
provider is a registry concern, not a stage concern. Part of **Department 03 (Intelligence)**.

> 📖 [Dept 03 — Intelligence](../../../docs/departments/03-intelligence/README.md)

## Contract

```python
class LLMProvider(ABC):
    name: str
    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str
    def structured(self, prompt: str, schema: type[T],
                   system: str | None = None, max_tokens: int = 2048) -> T
```

## Selection + call flow

```mermaid
flowchart TD
    Stage[AIExtractor / AISynthesizer] --> ABC[[LLMProvider ABC]]
    Reg[get_provider settings/env] --> Pick{provider?}
    Pick -->|anthropic| AN[AnthropicProvider]
    Pick -->|openai| OA[OpenAIProvider]
    Pick -->|claude-session| CS[ClaudeSessionProvider<br/>clipboard, no API key]
    Pick -->|static mode| NU[NullProvider no-op]
    AN & OA & CS & NU --> ABC
    ABC --> Str[structured: ask JSON -> tolerant parse -> pydantic]
```

## Files

| File | Role |
|---|---|
| `base.py` | `LLMProvider` ABC + tolerant JSON parser + `LLMUnavailableError` |
| `registry.py` | `get_provider()` factory (settings/env driven) |
| `anthropic_provider.py` | Claude API |
| `openai_provider.py` | GPT-4o-mini |
| `claude_session_provider.py` | Interactive clipboard paste (no API key) |
| `null_provider.py` | No-op for `static` mode |

## Rules

Never import a concrete provider in a stage — use the ABC. No hardcoded keys (read from
settings/env). Add a provider by subclassing + registering. `structured()` has a default
(JSON + tolerant parse); override only for native tool-use APIs.
