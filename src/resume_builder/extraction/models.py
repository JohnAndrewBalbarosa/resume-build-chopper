from __future__ import annotations

from pydantic import BaseModel, Field

CHARS_PER_TOKEN = 4
DEFAULT_TOKEN_CAP = 3000
DEFAULT_CAP_CHARS = DEFAULT_TOKEN_CAP * CHARS_PER_TOKEN


class CleanedSource(BaseModel):
    """Normalized, token-lean output of P2, consumed by P3 (tagging)."""

    source_id: str
    kind: str  # "github_readme" | "github_code" | "website"
    title: str = ""
    text: str = ""
    section_hints: list[str] = Field(default_factory=list)
    truncated: bool = False
    degraded: bool = False
