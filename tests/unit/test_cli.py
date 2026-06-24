from __future__ import annotations

from typer.testing import CliRunner

from resume_builder.cli import app
from resume_builder.llm import LLMProvider, register_provider

runner = CliRunner()


class _FakeReviewProvider(LLMProvider):
    name = "fake-review"
    last_prompt: str | None = None
    last_system: str | None = None

    def complete(self, prompt, system=None, max_tokens=1024):
        type(self).last_prompt = prompt
        type(self).last_system = system
        return "# Critical Issues\n- Missing quantified impact"


def test_list_roles_command():
    result = runner.invoke(app, ["list-roles"])
    assert result.exit_code == 0
    assert "cybersecurity-blueteam" in result.stdout


def test_build_missing_role_fails():
    result = runner.invoke(
        app, ["build", "--mode", "static", "--gh-user", "x"]
    )
    assert result.exit_code != 0
    assert "--role" in result.stdout or "--role" in (result.stderr or "")


def test_review_command_uses_findings_only_prompt(tmp_path):
    register_provider("fake-review", lambda _: _FakeReviewProvider())
    resume = tmp_path / "resume.txt"
    resume.write_text("Jane Doe\nBuilt dashboard\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["review", "--docs", str(resume), "--llm-provider", "fake-review"],
    )

    assert result.exit_code == 0
    assert "Missing quantified impact" in result.stdout
    assert _FakeReviewProvider.last_prompt is not None
    assert "Built dashboard" in _FakeReviewProvider.last_prompt
    assert _FakeReviewProvider.last_system is not None
    assert "Resume Review Orchestrator" in _FakeReviewProvider.last_system
