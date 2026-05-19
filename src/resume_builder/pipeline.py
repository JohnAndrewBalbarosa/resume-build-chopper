"""Orchestrator. Wires concrete stages per mode and runs the build.

The pipeline is the only place that knows about mode (`ai` vs `static`). Every other
module operates on abstract interfaces and concrete inputs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .config import Settings, get_settings
from .extractors import AIExtractor, Extractor, StaticExtractor
from .llm import LLMProvider, get_provider
from .llm.null_provider import NullProvider
from .models import Mode, RawDocument, Repo, Resume, RoleSpec
from .renderers import get_renderer
from .role import AIRolePicker, RolePicker, StaticRolePicker
from .sources import DocumentSource, GitHubSource
from .synthesizers import AISynthesizer, StaticSynthesizer, Synthesizer

log = logging.getLogger(__name__)


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


class Pipeline:
    def __init__(
        self,
        mode: Mode,
        settings: Settings | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        self.mode = mode
        self.settings = settings or get_settings()
        self.llm = llm or self._resolve_llm(mode, self.settings)
        self.role_picker: RolePicker = self._make_role_picker()
        self.extractor: Extractor = self._make_extractor()
        self.synthesizer: Synthesizer = self._make_synthesizer()
        self.github = GitHubSource()
        self.docs = DocumentSource()

    # ---- public ----

    def run(self, inputs: BuildInputs) -> PipelineResult:
        role = self.role_picker.pick(inputs.role_selection)
        repos = self.github.collect(user=inputs.gh_user, include_readme=True)
        evidence = self.extractor.extract(repos, role)
        documents: list[RawDocument] = (
            self.docs.collect(inputs.docs_path) if inputs.docs_path else []
        )
        resume = self.synthesizer.build(role, repos, evidence, documents)
        paths = self._render_all(resume, inputs.formats, inputs.output_dir)
        return PipelineResult(resume=resume, output_paths=paths)

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
