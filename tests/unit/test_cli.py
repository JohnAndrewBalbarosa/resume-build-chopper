from __future__ import annotations

from typer.testing import CliRunner

from resume_builder.cli import app

runner = CliRunner()


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
