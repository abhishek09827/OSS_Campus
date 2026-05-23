"""Pydantic-style request and response models for the API."""

from __future__ import annotations

from app._compat import BaseModel, Field
from app.scorer.readiness import ReadinessReport


class AnalyseRequest(BaseModel):
    """Request payload for the analysis endpoint."""

    github_username: str = Field(description="GitHub username to analyse.")
    jd_text: str = Field(description="Raw job description text.")


class SimilarRequest(BaseModel):
    """Request payload for similarity lookup."""

    summary: str = Field(description="Summary text to search against past reports.")


class ErrorResponse(BaseModel):
    """Structured error response."""

    error_code: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Human-readable error message.")


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: str = Field(description="Health status.")
    coral_available: bool = Field(description="Whether Coral is installed and runnable.")


class HistoryResponse(BaseModel):
    """History endpoint response wrapper."""

    items: list[ReadinessReport] = Field(description="Historical readiness reports.")

