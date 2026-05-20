"""Application settings and Coral CLI helper utilities."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app._compat import BaseSettings


class Settings(BaseSettings):
    """Environment-backed application settings."""

    openrouter_api_key: str | None = None
    github_token: str | None = None
    database_url: str = "postgresql://compass:compass@localhost:5432/compass"
    coral_bin: str = "coral"
    linkedin_access_token: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


def run_coral(sql: str) -> list[dict[str, Any]]:
    """Run a Coral SQL string and return a parsed JSON array.

    Parameters
    ----------
    sql:
        SQL text to execute via the Coral CLI.
    """
    settings = get_settings()
    command = [settings.coral_bin, "sql", sql, "--format", "json"]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return []
    except OSError:
        return []

    if completed.returncode != 0:
        return []

    stdout = completed.stdout.strip()
    if not stdout:
        return []
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return payload
    return [payload]
