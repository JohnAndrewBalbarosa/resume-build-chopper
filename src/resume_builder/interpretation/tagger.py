from __future__ import annotations

from ..classification.industry import TaggedProject
from ..llm.base import LLMProvider
from ..core.principles import HARVARD_PRINCIPLES
from .models import RetrievedSource

_TAGGER_SYSTEM = (
    "You tag ONE candidate source by INDUSTRY for an industry-first resume system. "
    "industries = industry/domain NAMES (e.g. 'artificial intelligence', 'cybersecurity'), never "
    "skills. A source may have MULTIPLE industries when its real components justify them (a web app "
    "with security features is web AND cybersecurity). Put skills only in skill_subtags. Separate "
    "quantitative_impact (numbers from the text) from qualitative_impact; never invent numbers. "
    "Be concise.\n\n"
) + HARVARD_PRINCIPLES


class ProjectTagger:
    """Tags a single RetrievedSource into a TaggedProject. Raises on LLM/parse failure —
    ParallelTagRunner owns per-source isolation (bounded retry + tracked miss)."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def tag(self, source: RetrievedSource) -> TaggedProject:
        prompt = (
            f"Source id: {source.source_id}\nKind: {source.kind}\nTitle: {source.title}\n\n"
            f"Content:\n{source.text}\n\n"
            "Return the tagged record (industries, skill_subtags, summary, "
            "quantitative_impact, qualitative_impact)."
        )
        tagged = self._llm.structured(
            prompt, schema=TaggedProject, system=_TAGGER_SYSTEM, max_tokens=1024
        )
        tagged.repo_full_name = source.source_id
        return tagged
