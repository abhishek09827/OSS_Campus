"""Subprocess wrapper for running Coral SQL queries."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class CoralQueryError(RuntimeError):
    """Raised when a Coral query fails."""


class CoralRunner:
    """Run Coral SQL queries through the Coral CLI."""

    def __init__(self, coral_bin: str = "coral") -> None:
        self.coral_bin = coral_bin

    def query(self, sql: str) -> list[dict[str, Any]]:
        """Run a Coral SQL query via subprocess and parse JSON output."""
        try:
            completed = subprocess.run(
                [self.coral_bin, "sql", sql, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CoralQueryError("Coral query timed out after 30 seconds") from exc
        except OSError as exc:
            raise CoralQueryError(f"Unable to start Coral CLI: {exc}") from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "unknown error"
            raise CoralQueryError(f"Coral query failed: {stderr}")

        stdout = completed.stdout.strip()
        if not stdout:
            return []
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise CoralQueryError(f"Coral returned invalid JSON: {stdout[:200]}") from exc
        if isinstance(payload, list):
            return payload
        return [payload]

    def query_file(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Read SQL from a file, apply string substitution, and execute it."""
        sql_path = Path(path)
        sql = sql_path.read_text(encoding="utf-8")
        if params:
            for key, value in params.items():
                sql = sql.replace("{" + key + "}", str(value))
        return self.query(sql)

