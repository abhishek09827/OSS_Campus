"""Typed Coral result schemas used across the agent."""

from __future__ import annotations

from datetime import date

from app._compat import BaseModel, Field


class ContributionRow(BaseModel):
    """Contribution strength metrics per repository."""

    repo: str = Field(description="Repository full name.")
    merged_prs: int = Field(description="Merged pull requests in the repo.")
    review_comments: int = Field(description="Review comments authored.")
    issues_opened: int = Field(description="Issues opened by the developer.")
    last_activity_date: date = Field(description="Most recent contribution date.")


class RoleAlignmentRow(BaseModel):
    """Readiness alignment against a required repo."""

    repo: str = Field(description="Repository full name.")
    required_by_jd: bool = Field(description="Whether the JD explicitly requires this repo.")
    my_merged_prs: int = Field(description="Merged PR count in this repo.")
    contribution_percentile: float = Field(description="Percentile of contribution strength.")
    gap_score: float = Field(description="Gap severity from 0 to 1.")


class NextContributionRow(BaseModel):
    """Actionable next issue suggestion."""

    repo: str = Field(description="Repository full name.")
    issue_number: int = Field(description="Issue number.")
    issue_title: str = Field(description="Issue title.")
    issue_url: str = Field(description="Issue URL.")
    matching_skills: list[str] = Field(description="Skills that match the JD.")
    estimated_days: int = Field(description="Estimated days to complete.")
    score_impact: int = Field(description="Estimated readiness score lift.")


class TrajectoryRow(BaseModel):
    """Monthly contribution velocity snapshot."""

    month: str = Field(description="YYYY-MM month label.")
    merged_prs: int = Field(description="Merged PR count in the month.")
    repos_contributed_to: int = Field(description="Unique repos touched in the month.")
    new_repos: int = Field(description="New repos first contributed to in the month.")

