"""Tests for the agent wiring and streaming analysis."""

from __future__ import annotations

import json

from app.agent.agent import build_agent
from app.api.models import AnalyseRequest
from app.api import routes
from app.coral.schemas import ContributionRow, NextContributionRow, RoleAlignmentRow, TrajectoryRow
from app.jd_parser.parser import JobDescription
from app.scorer.readiness import NextContribution, ReadinessReport, ContributionBreakdown


def test_agent_calls_tools_in_order(monkeypatch):
    """The agent executor should call the five tools in sequence."""
    order = []

    def fake_query_file(path, params=None):
        order.append(path)
        return []

    monkeypatch.setattr(routes, "store", routes.store)
    monkeypatch.setattr("app.agent.tools.runner.query_file", fake_query_file)
    agent = build_agent()
    agent.invoke({"github_username": "alice", "input": "alice"})
    assert order == [
        "queries/contribution_strength.sql",
        "queries/role_alignment.sql",
        "queries/gap_analysis.sql",
        "queries/trajectory.sql",
        "queries/next_contributions.sql",
    ]


def test_agent_produces_readiness_report(monkeypatch):
    """The scorer should produce a readiness report object."""
    jd = JobDescription(
        company="dbt Labs",
        role="Data Engineer",
        required_skills=["dbt"],
        preferred_oss_repos=["dbt-labs/dbt-core"],
        preferred_languages=["python"],
        experience_years_min=3,
        nice_to_have=[],
        raw_text="sample",
    )
    report = routes.scorer.compute(
        username="alice",
        jd=jd,
        contribution_rows=[
            ContributionRow(
                repo="dbt-labs/dbt-core",
                merged_prs=1,
                review_comments=0,
                issues_opened=0,
                last_activity_date="2026-05-01",
            )
        ],
        alignment_rows=[
            RoleAlignmentRow(
                repo="dbt-labs/dbt-core",
                required_by_jd=True,
                my_merged_prs=1,
                contribution_percentile=50.0,
                gap_score=0.6,
            )
        ],
        gap_rows=[],
        trajectory_rows=[TrajectoryRow(month="2026-05", merged_prs=1, repos_contributed_to=1, new_repos=0)],
        next_rows=[
            NextContributionRow(
                repo="apache/spark",
                issue_number=1,
                issue_title="Fix docs",
                issue_url="https://github.com/apache/spark/issues/1",
                matching_skills=["python"],
                estimated_days=3,
                score_impact=5,
            )
        ],
        llm_synthesis="synthetic",
    )
    assert isinstance(report.model_dump(), dict)
    assert report.github_username == "alice"


def test_streaming_response(monkeypatch):
    """The analyse route should stream status updates and a final report."""
    fake_report = ReadinessReport(
        github_username="alice",
        target_company="dbt Labs",
        target_role="Data Engineer",
        readiness_score=64,
        readiness_label="Strong candidate",
        breakdown=ContributionBreakdown(
            merged_prs_in_required_repos=1,
            merge_rate_avg=80.0,
            months_since_last_contribution=1,
            unique_repos_contributed=1,
            trajectory="steady",
        ),
        strengths=["good"],
        gaps=["gap"],
        next_contributions=[
            NextContribution(
                repo="apache/spark",
                issue_number=1,
                issue_title="Fix docs",
                issue_url="https://github.com/apache/spark/issues/1",
                why_this_one="best next move",
                estimated_days=3,
                score_impact=5,
            ),
            NextContribution(
                repo="apache/spark",
                issue_number=2,
                issue_title="Add tests",
                issue_url="https://github.com/apache/spark/issues/2",
                why_this_one="best next move",
                estimated_days=3,
                score_impact=5,
            ),
            NextContribution(
                repo="apache/spark",
                issue_number=3,
                issue_title="Improve docs",
                issue_url="https://github.com/apache/spark/issues/3",
                why_this_one="best next move",
                estimated_days=3,
                score_impact=5,
            ),
        ],
        summary="summary",
    )

    monkeypatch.setattr(routes.parser, "parse", lambda raw: JobDescription(
        company="dbt Labs",
        role="Data Engineer",
        required_skills=["dbt"],
        preferred_oss_repos=["dbt-labs/dbt-core"],
        preferred_languages=["python"],
        experience_years_min=3,
        nice_to_have=[],
        raw_text=raw,
    ))
    monkeypatch.setattr(routes.parser, "to_coral_file", lambda jd, path: None)
    monkeypatch.setattr(routes.store, "save", lambda report: None)
    monkeypatch.setattr(routes, "build_agent", lambda: type("E", (), {"invoke": lambda self, payload: {"output": {"ok": True}}})())
    monkeypatch.setattr(routes.scorer, "compute", lambda **kwargs: fake_report)

    response = routes.analyse(AnalyseRequest(github_username="alice", jd_text="Hiring data engineer"))
    assert response.media_type == "application/x-ndjson"
    lines = list(response.content)
    assert any("parsing_jd" in line for line in lines)
    assert any("complete" in line for line in lines)

