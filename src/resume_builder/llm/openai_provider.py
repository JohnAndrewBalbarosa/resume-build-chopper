"""OpenAI provider (optional — install with `pip install 'resume-build-chopper[openai]'`)."""

from __future__ import annotations

from .base import LLMProvider, LLMUnavailableError


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None, model: str) -> None:
        if not api_key:
            raise LLMUnavailableError("OPENAI_API_KEY is not set.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMUnavailableError(
                "`openai` package not installed. Install with `pip install 'resume-build-chopper[openai]'`."
            ) from exc
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
