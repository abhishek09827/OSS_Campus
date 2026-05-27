"""Tests for readiness scoring."""

from __future__ import annotations

from datetime import date

from app.coral.schemas import ContributionRow, NextContributionRow, RoleAlignmentRow, TrajectoryRow
from app.jd_parser.parser import JobDescription
from app.scorer.readiness import ReadinessScorer


def _sample_jd():
    return JobDescription(
        company="dbt Labs",
        role="Data Engineer",
        required_skills=["dbt", "python"],
        preferred_oss_repos=["dbt-labs/dbt-core", "apache/airflow"],
        preferred_languages=["python"],
        experience_years_min=3,
        nice_to_have=[],
        raw_text="sample",
    )


def test_zero_contributions_scores_zero():
    """No contributions should yield a zero score."""
    scorer = ReadinessScorer()
    report = scorer.compute(
        username="alice",
        jd=_sample_jd(),
        contribution_rows=[],
        alignment_rows=[],
        gap_rows=[],
        trajectory_rows=[],
        next_rows=[],
        llm_synthesis="",
    )
    assert report.readiness_score == 0
    assert report.readiness_label == "Not ready"


def test_threshold_labels():
    """The score thresholds should map to the expected labels."""
    scorer = ReadinessScorer()
    assert scorer._label(10) == "Not ready"
    assert scorer._label(50) == "Getting there"
    assert scorer._label(70) == "Strong candidate"
    assert scorer._label(90) == "Apply now"


def test_compute_produces_bounded_score():
    """Scores should always stay within 0-100."""
    scorer = ReadinessScorer()
    report = scorer.compute(
        username="alice",
        jd=_sample_jd(),
        contribution_rows=[
            ContributionRow(
                repo="dbt-labs/dbt-core",
                merged_prs=10,
                review_comments=2,
                issues_opened=1,
                last_activity_date=date.today(),
            )
        ],
        alignment_rows=[
            RoleAlignmentRow(
                repo="dbt-labs/dbt-core",
                required_by_jd=True,
                my_merged_prs=10,
                contribution_percentile=90.0,
                gap_score=0.1,
            )
        ],
        gap_rows=[],
        trajectory_rows=[
            TrajectoryRow(month="2026-04", merged_prs=1, repos_contributed_to=1, new_repos=0),
            TrajectoryRow(month="2026-05", merged_prs=4, repos_contributed_to=2, new_repos=1),
        ],
        next_rows=[
            NextContributionRow(
                repo="apache/spark",
                issue_number=1,
                issue_title="Improve docs",
                issue_url="https://github.com/apache/spark/issues/1",
                matching_skills=["python"],
                estimated_days=3,
                score_impact=5,
            )
        ],
        llm_synthesis="synthetic",
    )
    assert 0 <= report.readiness_score <= 100
    assert len(report.next_contributions) == 3
    assert len(report.strengths) == 3
    assert len(report.gaps) == 3

