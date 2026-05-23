"""FastAPI route definitions for OSS Compass."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Generator

from app._compat import FastAPI, HTTPException, StreamingResponse, status
from app.agent.agent import build_agent
from app.api.models import AnalyseRequest, ErrorResponse, HealthResponse, HistoryResponse, SimilarRequest
from app.config import get_settings
from app.coral.runner import CoralRunner
from app.jd_parser.parser import JDParser
from app.memory.store import AnalysisStore
from app.scorer.readiness import ReadinessScorer


app = FastAPI()
parser = JDParser()
scorer = ReadinessScorer()
store = AnalysisStore()
runner = CoralRunner()


def _coral_available() -> bool:
    """Check whether the Coral CLI is available."""
    try:
        completed = subprocess.run(["coral", "--version"], capture_output=True, text=True, timeout=10, check=False)
        return completed.returncode == 0
    except Exception:
        return False


def _build_report(username: str, jd_text: str) -> dict[str, Any]:
    """Run the full analysis pipeline and return a readiness report."""
    jd = parser.parse(jd_text)
    coral_dir = Path("jd_requirements")
    parser.to_coral_file(jd, ".")

    contribution_rows = []
    alignment_rows = []
    gap_rows = []
    trajectory_rows = []
    next_rows = []

    agent = build_agent()
    agent_output = agent.invoke({"github_username": username, "input": username})
    llm_synthesis = json.dumps(agent_output.get("output", {}), default=str)

    report = scorer.compute(
        username=username,
        jd=jd,
        contribution_rows=contribution_rows,
        alignment_rows=alignment_rows,
        gap_rows=gap_rows,
        trajectory_rows=trajectory_rows,
        next_rows=next_rows,
        llm_synthesis=llm_synthesis,
    )
    store.save(report)
    return report.model_dump()


@app.post("/analyse")
def analyse(payload: AnalyseRequest) -> StreamingResponse:
    """Analyse a GitHub profile against a job description."""
    def stream() -> Generator[str, None, None]:
        try:
            yield json.dumps({"step": "parsing_jd"}) + "\n"
            jd = parser.parse(payload.jd_text)
            yield json.dumps({"step": "writing_coral_source"}) + "\n"
            parser.to_coral_file(jd, ".")
            yield json.dumps({"step": "running_agent"}) + "\n"
            agent = build_agent()
            agent_output = agent.invoke({"github_username": payload.github_username, "input": payload.github_username})
            report = scorer.compute(
                username=payload.github_username,
                jd=jd,
                contribution_rows=[],
                alignment_rows=[],
                gap_rows=[],
                trajectory_rows=[],
                next_rows=[],
                llm_synthesis=json.dumps(agent_output.get("output", {}), default=str),
            )
            store.save(report)
            yield json.dumps({"step": "complete", "report": report.model_dump()}) + "\n"
        except Exception as exc:
            yield json.dumps({"error_code": "analysis_failed", "message": str(exc)}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.get("/history/{github_username}")
def history(github_username: str) -> dict[str, Any]:
    """Return all past analyses for a username."""
    items = store.get_user_history(github_username)
    return HistoryResponse(items=items).model_dump()


@app.get("/similar")
def similar(summary: str | None = None) -> dict[str, Any]:
    """Return similar past analyses for a summary string."""
    if not summary:
        return {"items": []}
    items = store.find_similar(summary)
    return HistoryResponse(items=items).model_dump()


@app.get("/health")
def health() -> dict[str, Any]:
    """Health check endpoint."""
    return HealthResponse(status="ok", coral_available=_coral_available()).model_dump()
