"""Basic CLI smoke test using Typer's CliRunner."""

from __future__ import annotations

from typer.testing import CliRunner

from doc2latex.cli import app


def test_help_runs():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "convert" in result.stdout.lower()


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "doc2latex" in result.stdout
