"""Tests for the Coral subprocess runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.coral.runner import CoralQueryError, CoralRunner


class DummyCompleted:
    def __init__(self, returncode=0, stdout="[]", stderr="") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_query_parses_json(monkeypatch):
    """A successful Coral call should parse a JSON array."""
    def fake_run(*args, **kwargs):
        return DummyCompleted(stdout=json.dumps([{"repo": "dbt-labs/dbt-core"}]))

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CoralRunner("coral")
    rows = runner.query("SELECT 1")
    assert rows == [{"repo": "dbt-labs/dbt-core"}]


def test_query_raises_on_non_zero(monkeypatch):
    """Non-zero exit codes should raise CoralQueryError."""
    def fake_run(*args, **kwargs):
        return DummyCompleted(returncode=1, stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CoralRunner("coral")
    with pytest.raises(CoralQueryError) as exc:
        runner.query("SELECT 1")
    assert "boom" in str(exc.value)


def test_query_timeout(monkeypatch):
    """Timeouts should become CoralQueryError."""
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="coral", timeout=30)

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CoralRunner("coral")
    with pytest.raises(CoralQueryError):
        runner.query("SELECT 1")


def test_query_file_substitution(tmp_path, monkeypatch):
    """query_file should substitute parameters before execution."""
    sql_file = tmp_path / "sample.sql"
    sql_file.write_text("SELECT '{github_username}' AS username;", encoding="utf-8")

    captured = {}

    def fake_query(self, sql):
        captured["sql"] = sql
        return [{"ok": True}]

    monkeypatch.setattr(CoralRunner, "query", fake_query)
    runner = CoralRunner("coral")
    rows = runner.query_file(str(sql_file), {"github_username": "alice"})
    assert rows == [{"ok": True}]
    assert "alice" in captured["sql"]

