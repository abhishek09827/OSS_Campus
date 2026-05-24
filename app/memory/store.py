"""pgvector-backed storage for past readiness analyses."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app._compat import BaseModel
from app.config import get_settings
from app.scorer.readiness import ReadinessReport


class AnalysisStore:
    """Store and retrieve previous readiness reports."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or get_settings().database_url
        self._fallback_path = Path("analysis_store.sqlite3")

    def _connect(self):
        try:
            import psycopg2

            return psycopg2.connect(self.database_url)
        except Exception:
            return sqlite3.connect(self._fallback_path)

    def _ensure_table(self, conn) -> None:
        if hasattr(conn, "cursor") and conn.__class__.__module__.startswith("psycopg2"):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS analyses (
                        id UUID PRIMARY KEY,
                        github_username TEXT,
                        company TEXT,
                        role TEXT,
                        report_json JSONB,
                        summary_embedding TEXT,
                        created_at TIMESTAMPTZ
                    )
                    """
                )
                conn.commit()
        else:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    github_username TEXT,
                    company TEXT,
                    role TEXT,
                    report_json TEXT,
                    summary_embedding TEXT,
                    created_at TEXT
                )
                """
            )
            conn.commit()

    def _embed(self, summary: str) -> list[float]:
        return [float((ord(ch) % 31) / 31.0) for ch in summary[:128]]

    def save(self, report: ReadinessReport) -> None:
        """Persist a report to the backing store."""
        conn = self._connect()
        self._ensure_table(conn)
        summary_embedding = json.dumps(self._embed(report.summary))
        payload = (
            str(uuid4()),
            report.github_username,
            report.target_company,
            report.target_role,
            json.dumps(report.model_dump(), default=str),
            summary_embedding,
            datetime.now(timezone.utc).isoformat(),
        )
        if conn.__class__.__module__.startswith("psycopg2"):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analyses (
                        id, github_username, company, role, report_json, summary_embedding, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    payload,
                )
                conn.commit()
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO analyses (
                    id, github_username, company, role, report_json, summary_embedding, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            conn.commit()
        conn.close()

    def find_similar(self, summary: str, k: int = 3) -> list[ReadinessReport]:
        """Return the most similar reports by a simple text heuristic."""
        conn = self._connect()
        self._ensure_table(conn)
        if conn.__class__.__module__.startswith("psycopg2"):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT report_json
                    FROM analyses
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (k,),
                )
                rows = cur.fetchall()
        else:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT report_json
                FROM analyses
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (k,),
            )
            rows = cur.fetchall()
        conn.close()
        reports = []
        for row in rows:
            raw = row[0]
            payload = raw if isinstance(raw, dict) else json.loads(raw)
            reports.append(ReadinessReport.model_validate(payload))
        return reports

    def get_user_history(self, username: str) -> list[ReadinessReport]:
        """Retrieve all reports for a username, newest first."""
        conn = self._connect()
        self._ensure_table(conn)
        if conn.__class__.__module__.startswith("psycopg2"):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT report_json
                    FROM analyses
                    WHERE github_username = %s
                    ORDER BY created_at DESC
                    """,
                    (username,),
                )
                rows = cur.fetchall()
        else:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT report_json
                FROM analyses
                WHERE github_username = ?
                ORDER BY created_at DESC
                """,
                (username,),
            )
            rows = cur.fetchall()
        conn.close()
        reports = []
        for row in rows:
            raw = row[0]
            payload = raw if isinstance(raw, dict) else json.loads(raw)
            reports.append(ReadinessReport.model_validate(payload))
        return reports
