"""Compute readiness scores and produce the final ReadinessReport."""

from __future__ import annotations

from datetime import date
from typing import Any

from app._compat import BaseModel, Field
from app.coral.schemas import ContributionRow, NextContributionRow, RoleAlignmentRow, TrajectoryRow
from app.jd_parser.parser import JobDescription


class ContributionBreakdown(BaseModel):
    """Feature breakdown used to compute readiness."""

    merged_prs_in_required_repos: int = Field(description="Merged PRs in repos relevant to the JD.")
    merge_rate_avg: float = Field(description="Average merge rate across relevant repos.")
    months_since_last_contribution: int = Field(description="Months since the most recent contribution.")
    unique_repos_contributed: int = Field(description="Total unique repos contributed to.")
    trajectory: str = Field(description='Trajectory classification: "accelerating", "steady", or "declining".')


class NextContribution(BaseModel):
    """A single recommended next OSS contribution."""

    repo: str = Field(description="Repository full name.")
    issue_number: int = Field(description="Issue number.")
    issue_title: str = Field(description="Issue title.")
    issue_url: str = Field(description="Issue URL.")
    why_this_one: str = Field(description="Why this issue is the best next move.")
    estimated_days: int = Field(description="Estimated days to complete.")
    score_impact: int = Field(description="Estimated points added to the readiness score.")


class ReadinessReport(BaseModel):
    """Final analysis report shown to the user."""

    github_username: str = Field(description="Analyzed GitHub username.")
    target_company: str = Field(description="Target company extracted from the JD.")
    target_role: str = Field(description="Target role extracted from the JD.")
    readiness_score: int = Field(description="Readiness score from 0 to 100.")
    readiness_label: str = Field(description='One of "Not ready", "Getting there", "Strong candidate", "Apply now".')
    breakdown: ContributionBreakdown = Field(description="Score breakdown object.")
    strengths: list[str] = Field(description="Three strengths.")
    gaps: list[str] = Field(description="Three gaps.")
    next_contributions: list[NextContribution] = Field(description="Exactly three next contributions.")
    summary: str = Field(description="Two-sentence plain English verdict.")


class ReadinessScorer:
    """Turn raw Coral query rows into a final readiness report."""

    def _label(self, score: int) -> str:
        if score <= 40:
            return "Not ready"
        if score <= 60:
            return "Getting there"
        if score <= 80:
            return "Strong candidate"
        return "Apply now"

    def _trajectory_label(self, trajectory_rows: list[TrajectoryRow]) -> str:
        if len(trajectory_rows) < 2:
            return "steady"
        first = trajectory_rows[0].merged_prs
        last = trajectory_rows[-1].merged_prs
        if last > first:
            return "accelerating"
        if last < first:
            return "declining"
        return "steady"

    def _merge_rate_avg(self, alignment_rows: list[RoleAlignmentRow], contribution_rows: list[ContributionRow]) -> float:
        if alignment_rows:
            values = []
            for row in alignment_rows:
                value = getattr(row, "my_merge_rate", None)
                if value is None:
                    value = getattr(row, "contribution_percentile", 0.0)
                values.append(float(value))
            return round(sum(values) / len(values), 2)
        if not contribution_rows:
            return 0.0
        # Fallback for when only contribution rows are available.
        merged = sum(max(row.merged_prs, 0) for row in contribution_rows)
        total_prs = max(merged, 1)
        if total_prs == 0:
            return 0.0
        return round((merged / max(total_prs, 1)) * 100.0, 2)

    def _last_activity_days(self, contribution_rows: list[ContributionRow]) -> int:
        if not contribution_rows:
            return 9999
        dates = [row.last_activity_date for row in contribution_rows if row.last_activity_date]
        if not dates:
            return 9999
        latest = max(dates)
        today = date.today()
        return max(0, (today - latest).days)

    def _last_activity_months(self, contribution_rows: list[ContributionRow]) -> int:
        days = self._last_activity_days(contribution_rows)
        if days >= 9999:
            return 999
        return days // 30

    def compute(
        self,
        username: str,
        jd: JobDescription,
        contribution_rows: list[ContributionRow],
        alignment_rows: list[RoleAlignmentRow],
        gap_rows: list[Any],
        trajectory_rows: list[TrajectoryRow],
        next_rows: list[NextContributionRow],
        llm_synthesis: str,
    ) -> ReadinessReport:
        """Compute a final readiness report from all raw inputs."""
        merged_in_required = sum(row.merged_prs for row in contribution_rows)
        merge_rate_avg = self._merge_rate_avg(alignment_rows, contribution_rows)
        days_since_last = self._last_activity_days(contribution_rows)
        months_since_last = self._last_activity_months(contribution_rows)
        unique_repos = len({row.repo for row in contribution_rows})
        trajectory_label = self._trajectory_label(trajectory_rows)

        merged_prs_score = min(merged_in_required * 6, 30)
        quality_score = min(round(merge_rate_avg * 0.2), 20)
        recency_score = 20 if days_since_last < 60 else 10 if days_since_last < 180 else 0
        diversity_score = min(unique_repos * 3, 15)
        trajectory_score = 15 if trajectory_label == "accelerating" else 8 if trajectory_label == "steady" else 0
        score = max(0, min(100, merged_prs_score + quality_score + recency_score + diversity_score + trajectory_score))

        alignment_rows_sorted = sorted(alignment_rows, key=lambda row: (row.gap_score, row.my_merged_prs), reverse=True)
        strengths = [
            f"Contributions in {row.repo} already show momentum." for row in contribution_rows[:3]
        ] or ["No OSS contributions yet, so there is room to build a visible baseline."]
        while len(strengths) < 3:
            strengths.append("You already have adjacent skills that map to the target role.")

        gaps = []
        if alignment_rows_sorted:
            for row in alignment_rows_sorted[:3]:
                gaps.append(f"{row.repo} has a gap score of {row.gap_score:.2f} against the JD.")
        elif gap_rows:
            for row in gap_rows[:3]:
                repo = getattr(row, "repo_name", None) or getattr(row, "repo", "unknown repo")
                gaps.append(f"{repo} needs more targeted contributions.")
        else:
            gaps = ["The JD-relevant repos are not yet well covered."]
        while len(gaps) < 3:
            gaps.append("More merged PRs in the JD-aligned repos would materially improve readiness.")

        next_contributions: list[NextContribution] = []
        for row in next_rows[:3]:
            next_contributions.append(
                NextContribution(
                    repo=row.repo,
                    issue_number=row.issue_number,
                    issue_title=row.issue_title,
                    issue_url=row.issue_url,
                    why_this_one=(
                        f"It directly targets the largest repo gap and maps to the JD."
                    ),
                    estimated_days=row.estimated_days,
                    score_impact=row.score_impact,
                )
            )
        while len(next_contributions) < 3:
            index = len(next_contributions) + 1
            next_contributions.append(
                NextContribution(
                    repo=jd.preferred_oss_repos[0] if jd.preferred_oss_repos else "unknown/repo",
                    issue_number=index,
                    issue_title="Find a good-first-issue in the target repo",
                    issue_url="https://github.com",
                    why_this_one="It is the fastest way to convert intent into a visible contribution.",
                    estimated_days=3,
                    score_impact=5,
                )
            )

        summary = (
            f"{username} is {self._label(score).lower()} for {jd.role} at {jd.company}. "
            f"{llm_synthesis.strip() or 'The strongest next move is to focus on the JD-aligned repos and ship a few targeted PRs.'}"
        )

        return ReadinessReport(
            github_username=username,
            target_company=jd.company,
            target_role=jd.role,
            readiness_score=score,
            readiness_label=self._label(score),
            breakdown=ContributionBreakdown(
                merged_prs_in_required_repos=merged_in_required,
                merge_rate_avg=merge_rate_avg,
                months_since_last_contribution=months_since_last,
                unique_repos_contributed=unique_repos,
                trajectory=trajectory_label,
            ),
            strengths=strengths[:3],
            gaps=gaps[:3],
            next_contributions=next_contributions[:3],
            summary=summary[:500],
        )
