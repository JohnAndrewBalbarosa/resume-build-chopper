"""Orchestrator. Wires concrete stages per mode and runs the build.

The pipeline is the only place that knows about mode (`ai` vs `static`). Every other
module operates on abstract interfaces and concrete inputs.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from .config import Settings, get_settings
from .extractors import AIExtractor, Extractor, StaticExtractor
from .llm import LLMProvider, get_provider
from .llm.null_provider import NullProvider
from .models import Mode, RawDocument, Repo, Resume, ResumeAchievement, ResumeProject, RoleSpec
from .renderers import get_renderer
from .role import AIRolePicker, RolePicker, StaticRolePicker
from .sources import DocumentSource, GitHubSource
from .sources.social import (
    CollectResult,
    ScrapeConfig,
    SocialAggregator,
    build_default_aggregator,
    load_scrape_config,
)
from .synthesizers import AISynthesizer, StaticSynthesizer, Synthesizer

log = logging.getLogger(__name__)


def _achievements_from_social(result: CollectResult) -> list[ResumeAchievement]:
    """Convert aggregator output into a flat, render-ready list."""
    out: list[ResumeAchievement] = []
    for post in result.posts:
        title = post.text.strip().splitlines()[0][:120] if post.text else f"{post.vendor} post"
        out.append(
            ResumeAchievement(
                title=title,
                source=post.vendor,
                url=post.url,
                date=post.posted_at.date().isoformat() if post.posted_at else None,
                snippet=post.text[:400],
            )
        )
    for mention in result.mentions:
        title = (
            f"Mentioned by {mention.author_name}"
            if mention.author_name
            else f"{mention.vendor} mention"
        )
        out.append(
            ResumeAchievement(
                title=title,
                source=mention.vendor,
                url=mention.url,
                date=mention.posted_at.date().isoformat() if mention.posted_at else None,
                snippet=mention.text[:400],
            )
        )
    out.sort(key=lambda a: a.date or "", reverse=True)
    return out


# ---- role-aware achievement filtering ------------------------------------------


class _AchievementVerdict(BaseModel):
    """One LLM judgement about a candidate achievement."""

    index: int = Field(..., description="Index of the candidate in the input list.")
    relevant: bool = Field(
        ..., description="True only if it genuinely supports the TARGET ROLE."
    )
    focused_snippet: str | None = Field(
        None,
        description="The snippet trimmed to ONLY the role-relevant part, or null if relevant is false.",
    )


class _AchievementVerdicts(BaseModel):
    items: list[_AchievementVerdict] = Field(default_factory=list)


_ACHIEVEMENT_SYSTEM = (
    "You are a strict resume editor specializing one resume to one target role. "
    "You are given social/recognition posts that were dumped indiscriminately. "
    "Keep an item ONLY when it is a real achievement/recognition that a hiring manager for the "
    "TARGET ROLE would care about. Drop anything off-topic for the role — event hosting, "
    "influencer/gaming features, generic meetups, club initiations, and administrative thesis "
    "chores are NOT role achievements. When kept, rewrite focused_snippet to contain only the "
    "portion that speaks to the target role; strip promotional fluff. Be ruthless: if it does not "
    "clearly belong on a resume for THIS role, mark it not relevant."
)


def _role_terms(role: RoleSpec) -> list[str]:
    terms: list[str] = []
    terms += role.keywords
    terms += role.must_have_skills
    terms += role.nice_to_have
    # de-dup, drop empties, lowercase
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        key = t.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _keyword_relevant(text: str, terms: list[str]) -> bool:
    """Word-boundary, case-insensitive match so short acronyms (SOC, IDS) don't over-match."""
    hay = text.lower()
    for term in terms:
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", hay):
            return True
    return False


def _filter_achievements_by_role(
    candidates: list[ResumeAchievement],
    role: RoleSpec,
    llm: LLMProvider | None,
) -> list[ResumeAchievement]:
    """Keep only achievements relevant to the target role.

    AI verifies and segregates when a real provider is available; otherwise a strict
    keyword gate is used. Returns [] when nothing qualifies — we never pad the section.
    """
    if not candidates:
        return []

    use_ai = llm is not None and not isinstance(llm, NullProvider)
    if use_ai:
        try:
            return _filter_with_ai(candidates, role, llm)
        except Exception:  # noqa: BLE001 — any LLM/parse failure falls back to keywords
            log.warning("AI achievement filter failed; falling back to keyword gate.")

    terms = _role_terms(role)
    return [
        a
        for a in candidates
        if _keyword_relevant(f"{a.title}\n{a.snippet or ''}", terms)
    ]


def _filter_with_ai(
    candidates: list[ResumeAchievement],
    role: RoleSpec,
    llm: LLMProvider,
) -> list[ResumeAchievement]:
    listing = "\n".join(
        f"[{i}] {a.title}\n    {(a.snippet or '').strip()[:400]}"
        for i, a in enumerate(candidates)
    )
    prompt = (
        f"TARGET ROLE: {role.label}\n"
        f"Role keywords: {', '.join(role.keywords)}\n"
        f"Must-have skills: {', '.join(role.must_have_skills)}\n"
        f"Nice-to-have: {', '.join(role.nice_to_have)}\n\n"
        f"Candidate achievements:\n{listing}\n\n"
        "Return a verdict for every index."
    )
    verdicts = llm.structured(
        prompt, schema=_AchievementVerdicts, system=_ACHIEVEMENT_SYSTEM, max_tokens=2048
    )
    kept: list[ResumeAchievement] = []
    for v in verdicts.items:
        if not v.relevant or not (0 <= v.index < len(candidates)):
            continue
        src = candidates[v.index]
        kept.append(
            src.model_copy(update={"snippet": v.focused_snippet.strip()})
            if v.focused_snippet and v.focused_snippet.strip()
            else src
        )
    return kept


# ---- role-aware project filtering -----------------------------------------------


class _ProjectVerdict(BaseModel):
    """One LLM judgement about a candidate project."""

    index: int = Field(..., description="Index of the candidate in the input list.")
    relevant: bool = Field(
        ..., description="True only if the project genuinely demonstrates the TARGET ROLE."
    )
    focused_description: str | None = Field(
        None,
        description="The description rewritten for the target role, or null if not relevant.",
    )


class _ProjectVerdicts(BaseModel):
    items: list[_ProjectVerdict] = Field(default_factory=list)


_PROJECT_SYSTEM = (
    "You are a strict resume editor specializing one resume to one target role. "
    "Keep a project ONLY when it genuinely demonstrates skills a hiring manager for the "
    "TARGET ROLE would value. A project may be relevant to more than one role, but a "
    "compiler is not a machine-learning project and a static website is not a security "
    "project — judge by what the project actually is, not by which languages it lists. "
    "When kept, rewrite focused_description to emphasize the role-relevant angle. If it "
    "does not clearly belong on a resume for THIS role, mark it not relevant."
)


def _filter_projects_by_role(
    projects: list[ResumeProject],
    role: RoleSpec,
    llm: LLMProvider | None,
) -> list[ResumeProject]:
    """Keep only projects relevant to the target role (multi-role allowed).

    AI verifies and re-frames when a real provider is available; otherwise a keyword
    gate over name + tech + description is used. Returns [] when nothing qualifies.
    """
    if not projects:
        return []

    use_ai = llm is not None and not isinstance(llm, NullProvider)
    if use_ai:
        try:
            return _filter_projects_with_ai(projects, role, llm)
        except Exception:  # noqa: BLE001 — any LLM/parse failure falls back to keywords
            log.warning("AI project filter failed; falling back to keyword gate.")

    terms = _role_terms(role)
    return [
        p
        for p in projects
        if _keyword_relevant(f"{p.name}\n{' '.join(p.tech)}\n{p.description}", terms)
    ]


def _filter_projects_with_ai(
    projects: list[ResumeProject],
    role: RoleSpec,
    llm: LLMProvider,
) -> list[ResumeProject]:
    raise NotImplementedError  # implemented in Task 3


@dataclass
class PipelineResult:
    resume: Resume
    output_paths: list[Path]


@dataclass
class BuildInputs:
    gh_user: str
    role_selection: str
    docs_path: str | Path | None
    formats: list[str]
    output_dir: Path
    social_config_path: str | Path | None = None


class Pipeline:
    def __init__(
        self,
        mode: Mode,
        settings: Settings | None = None,
        llm: LLMProvider | None = None,
        social_aggregator: SocialAggregator | None = None,
    ) -> None:
        self.mode = mode
        self.settings = settings or get_settings()
        self.llm = llm or self._resolve_llm(mode, self.settings)
        self.role_picker: RolePicker = self._make_role_picker()
        self.extractor: Extractor = self._make_extractor()
        self.synthesizer: Synthesizer = self._make_synthesizer()
        self.github = GitHubSource()
        self.docs = DocumentSource()
        self.social = social_aggregator or build_default_aggregator()

    # ---- public ----

    def run(self, inputs: BuildInputs) -> PipelineResult:
        role = self.role_picker.pick(inputs.role_selection)
        repos = self.github.collect(user=inputs.gh_user, include_readme=True)
        evidence = self.extractor.extract(repos, role)
        documents: list[RawDocument] = (
            self.docs.collect(inputs.docs_path) if inputs.docs_path else []
        )
        resume = self.synthesizer.build(role, repos, evidence, documents)
        social_result = self._collect_social(inputs.social_config_path)
        if social_result is not None:
            candidates = _achievements_from_social(social_result)
            resume.achievements = _filter_achievements_by_role(candidates, role, self.llm)
        paths = self._render_all(resume, inputs.formats, inputs.output_dir)
        return PipelineResult(resume=resume, output_paths=paths)

    def _collect_social(
        self, path: str | Path | None
    ) -> CollectResult | None:
        if not path:
            return None
        try:
            config: ScrapeConfig = load_scrape_config(str(path))
        except Exception as exc:  # noqa: BLE001
            log.warning("social config %s could not be loaded: %s", path, exc)
            return None
        return self.social.collect(config)

    def render_only(
        self, resume: Resume, formats: list[str], output_dir: Path
    ) -> list[Path]:
        return self._render_all(resume, formats, output_dir)

    # ---- factories ----

    def _make_role_picker(self) -> RolePicker:
        if self.mode == Mode.AI:
            return AIRolePicker(self.llm)
        return StaticRolePicker(self.settings.roles_path)

    def _make_extractor(self) -> Extractor:
        if self.mode == Mode.AI:
            return AIExtractor(self.llm)
        return StaticExtractor(self.settings.regex_patterns_path)

    def _make_synthesizer(self) -> Synthesizer:
        if self.mode == Mode.AI:
            return AISynthesizer(self.llm)
        return StaticSynthesizer()

    @staticmethod
    def _resolve_llm(mode: Mode, settings: Settings) -> LLMProvider:
        if mode == Mode.STATIC:
            return NullProvider()
        return get_provider(settings=settings)

    def _render_all(
        self, resume: Resume, formats: list[str], output_dir: Path
    ) -> list[Path]:
        out: list[Path] = []
        for fmt in formats:
            renderer = get_renderer(fmt, self.settings.templates_dir)
            path = renderer.write(resume, output_dir)
            log.info("Wrote %s", path)
            out.append(path)
        return out
