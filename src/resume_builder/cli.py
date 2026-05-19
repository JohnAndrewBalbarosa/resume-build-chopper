"""Typer CLI entrypoint.

Examples:
    resume-build list-roles
    resume-build build --mode static --gh-user JohnDoe --role cybersecurity-blueteam \
        --docs ./my-resume.tex --output ./out --formats latex,md,json
    resume-build build --mode ai --gh-user JohnDoe --role-prompt "blue team SOC analyst" \
        --docs ./my-resume.pdf --output ./out
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from .config import get_settings
from .models import Mode
from .pipeline import BuildInputs, Pipeline
from .role import StaticRolePicker

app = typer.Typer(help="GitHub-aware role-targeted resume builder.", no_args_is_help=True)


def _parse_formats(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@app.command()
def list_roles() -> None:
    """List role ids available in config/roles.json."""
    settings = get_settings()
    picker = StaticRolePicker(settings.roles_path)
    for role in picker.list_available():
        typer.echo(f"  {role.id:30}  {role.label}")


@app.command()
def build(
    mode: Mode = typer.Option(Mode.STATIC, "--mode", help="ai | static"),
    gh_user: str = typer.Option(..., "--gh-user", help="GitHub username/org to scan."),
    role: str | None = typer.Option(None, "--role", help="Role id (static mode)."),
    role_prompt: str | None = typer.Option(
        None, "--role-prompt", help="Free-form role description (AI mode)."
    ),
    docs: Path | None = typer.Option(
        None, "--docs", help="Path to a resume file (PDF/DOCX/TEX) or a folder."
    ),
    formats: str = typer.Option(
        "latex,md,json,pdf",
        "--formats",
        help="Comma-separated output formats: latex, md, json, pdf.",
    ),
    output: Path = typer.Option(Path("./out"), "--output", help="Output directory."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Build a role-targeted resume."""
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    selection = role_prompt if mode == Mode.AI else role
    if not selection:
        flag = "--role-prompt" if mode == Mode.AI else "--role"
        raise typer.BadParameter(f"{flag} is required in {mode.value} mode.")

    pipeline = Pipeline(mode=mode)
    inputs = BuildInputs(
        gh_user=gh_user,
        role_selection=selection,
        docs_path=docs,
        formats=_parse_formats(formats),
        output_dir=output,
    )
    result = pipeline.run(inputs)
    typer.echo(f"\nGenerated for role: {result.resume.role.label}")
    typer.echo(f"Projects included: {len(result.resume.projects)}")
    for path in result.output_paths:
        typer.echo(f"  -> {path}")


if __name__ == "__main__":
    app()
