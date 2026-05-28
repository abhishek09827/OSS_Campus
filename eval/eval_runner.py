"""Evaluate the readiness scorer against synthetic profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.coral.schemas import ContributionRow, NextContributionRow, RoleAlignmentRow, TrajectoryRow
from app.jd_parser.parser import JobDescription
from app.scorer.readiness import ReadinessScorer
from eval.test_cases import TEST_CASES


class EvalRunner:
    """Run the readiness scorer on the synthetic test suite."""

    def __init__(self) -> None:
        self.scorer = ReadinessScorer()

    def _case_to_report(self, case: dict[str, Any]) -> dict[str, Any]:
        contributions = []
        alignment = []
        for repo, stats in case["mock_contributions"].items():
            contributions.append(
                ContributionRow(
                    repo=repo,
                    merged_prs=stats["merged_prs"],
                    review_comments=0,
                    issues_opened=0,
                    last_activity_date="2026-05-01",
                )
            )
            alignment.append(
                RoleAlignmentRow(
                    repo=repo,
                    required_by_jd=True,
                    my_merged_prs=stats["merged_prs"],
                    contribution_percentile=stats["merge_rate"] * 100,
                    gap_score=max(0.0, 1.0 - stats["merge_rate"]),
                )
            )
        jd = JobDescription(
            company=case["jd_company"],
            role=case["jd_role"],
            required_skills=["open source"],
            preferred_oss_repos=list(case["mock_contributions"].keys()),
            preferred_languages=["python"],
            experience_years_min=3,
            nice_to_have=[],
            raw_text="synthetic",
        )
        report = self.scorer.compute(
            username=case["github_username"],
            jd=jd,
            contribution_rows=contributions,
            alignment_rows=alignment,
            gap_rows=[],
            trajectory_rows=[TrajectoryRow(month="2026-04", merged_prs=1, repos_contributed_to=1, new_repos=0)],
            next_rows=[
                NextContributionRow(
                    repo=case["ground_truth_top_gap"],
                    issue_number=1,
                    issue_title="Improve docs",
                    issue_url=f"https://github.com/{case['ground_truth_top_gap']}/issues/1",
                    matching_skills=["python"],
                    estimated_days=3,
                    score_impact=5,
                )
            ],
            llm_synthesis="synthetic eval",
        )
        return report.model_dump()

    def run(self, output_path: str = "eval_report.json") -> dict[str, Any]:
        """Run the eval suite and write a report file."""
        results = []
        score_hits = 0
        label_hits = 0
        gap_hits = 0
        for case in TEST_CASES:
            report = self._case_to_report(case)
            score_ok = case["ground_truth_score_range"][0] <= report["readiness_score"] <= case["ground_truth_score_range"][1]
            label_ok = report["readiness_label"] == case["ground_truth_label"]
            top_gap = case["ground_truth_top_gap"].lower()
            next_repos = " ".join(item["repo"].lower() for item in report["next_contributions"])
            gap_text = " ".join(report["gaps"]).lower()
            top_gap_ok = top_gap in next_repos or top_gap in gap_text
            score_hits += int(score_ok)
            label_hits += int(label_ok)
            gap_hits += int(top_gap_ok)
            results.append(
                {
                    "case": case["name"],
                    "score": report["readiness_score"],
                    "label": report["readiness_label"],
                    "score_ok": score_ok,
                    "label_ok": label_ok,
                    "gap_ok": top_gap_ok,
                }
            )

        summary = {
            "score_accuracy": round(score_hits / len(TEST_CASES), 3),
            "label_accuracy": round(label_hits / len(TEST_CASES), 3),
            "gap_accuracy": round(gap_hits / len(TEST_CASES), 3),
        }
        summary["overall_accuracy"] = round(
            (summary["score_accuracy"] + summary["label_accuracy"] + summary["gap_accuracy"]) / 3, 3
        )
        payload = {"results": results, "summary": summary}
        Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload


if __name__ == "__main__":
    runner = EvalRunner()
    report = runner.run()
    print(json.dumps(report["summary"], indent=2))
