"""LangChain-style tools wrapping Coral SQL queries."""

from __future__ import annotations

import json
from pathlib import Path

from app._compat import Tool
from app.coral.runner import CoralRunner


runner = CoralRunner()


def _safe_query_file(path: str, params: dict[str, str]) -> list[dict]:
    """Execute a Coral query file and return an empty list on failure."""
    try:
        return runner.query_file(path, params)
    except Exception:
        return []


def _load_target_repos() -> str:
    """Read target repos from the parsed JD Coral file source when available."""
    repos_file = Path("jd_requirements") / "repos.json"
    if not repos_file.exists():
        return "'dbt-labs/dbt-core','apache/airflow'"
    try:
        payload = json.loads(repos_file.read_text(encoding="utf-8"))
        repos = [f"'{item['repo_name']}'" for item in payload if item.get("repo_name")]
        return ",".join(repos) or "'dbt-labs/dbt-core','apache/airflow'"
    except Exception:
        return "'dbt-labs/dbt-core','apache/airflow'"


contribution_strength_tool = Tool(
    name="contribution_strength",
    description=(
        "Use this to understand how strong a developer's OSS contribution history is. "
        "Input: GitHub username as a string."
    ),
    func=lambda username: _safe_query_file(
        "queries/contribution_strength.sql",
        {"github_username": username},
    ),
)


role_alignment_tool = Tool(
    name="role_alignment",
    description=(
        "Use this AFTER the JD has been parsed and saved to disk. "
        "Compares the developer's GitHub contributions against repos required by the job description."
    ),
    func=lambda username: _safe_query_file(
        "queries/role_alignment.sql",
        {"github_username": username},
    ),
)


gap_analysis_tool = Tool(
    name="gap_analysis",
    description="Find repos the JD cares about where the developer has a thin contribution history.",
    func=lambda username: _safe_query_file(
        "queries/gap_analysis.sql",
        {"github_username": username},
    ),
)


next_contributions_tool = Tool(
    name="next_contributions",
    description="Find actionable good-first-issues in gap repos.",
    func=lambda username: _safe_query_file(
        "queries/next_contributions.sql",
        {"target_repos_csv": _load_target_repos()},
    ),
)


trajectory_tool = Tool(
    name="trajectory",
    description="Inspect contribution velocity over the last 12 months.",
    func=lambda username: _safe_query_file(
        "queries/trajectory.sql",
        {"github_username": username},
    ),
)
