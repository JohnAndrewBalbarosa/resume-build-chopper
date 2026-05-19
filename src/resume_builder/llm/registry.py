"""Provider registry. Add new providers by registering them here.

Resolution order:
1. Explicit `provider_name` argument.
2. Settings.llm_provider env var.
3. `null` fallback (raises if used).
"""

from __future__ import annotations

from typing import Callable

from ..config import Settings, get_settings
from .anthropic_provider import AnthropicProvider
from .base import LLMProvider
from .null_provider import NullProvider
from .openai_provider import OpenAIProvider


def _build_anthropic(s: Settings) -> LLMProvider:
    return AnthropicProvider(api_key=s.anthropic_api_key, model=s.anthropic_model)


def _build_openai(s: Settings) -> LLMProvider:
    return OpenAIProvider(api_key=s.openai_api_key, model=s.openai_model)


def _build_null(_: Settings) -> LLMProvider:
    return NullProvider()


_REGISTRY: dict[str, Callable[[Settings], LLMProvider]] = {
    "anthropic": _build_anthropic,
    "openai": _build_openai,
    "null": _build_null,
}


def register_provider(name: str, factory: Callable[[Settings], LLMProvider]) -> None:
    """Public extension point for new providers."""
    _REGISTRY[name] = factory


def get_provider(provider_name: str | None = None, settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    name = provider_name or s.llm_provider or "null"
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown LLM provider: {name!r}. Available: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name](s)
