"""Parse job descriptions into structured data and Coral-ready JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from app._compat import BaseModel, BaseSettings, Field
from app.config import get_settings


class JobDescription(BaseModel):
    """Structured job description extracted from raw text."""

    company: str = Field(description="Company name from the JD.")
    role: str = Field(description="Target role title.")
    required_skills: list[str] = Field(description="Skills explicitly required in the JD.")
    preferred_oss_repos: list[str] = Field(description="Repo paths inferred from OSS mentions.")
    preferred_languages: list[str] = Field(description="Preferred languages mentioned in the JD.")
    experience_years_min: int = Field(description="Minimum years of experience.")
    nice_to_have: list[str] = Field(description="Optional nice-to-have skills.")
    raw_text: str = Field(description="Original raw job description text.")


class JDParser:
    """Parse raw job descriptions using OpenRouter and save Coral file sources."""

    def __init__(self, model: str = "anthropic/claude-3-haiku") -> None:
        self.model = model

    def _build_prompt(self, raw_jd: str) -> list[dict[str, str]]:
        system = (
            "You are a precise JD parser. Extract structured data. "
            "Return ONLY valid JSON matching the schema. No markdown, no explanation. "
            "The preferred_oss_repos field should be full GitHub repo paths like "
            '"dbt-labs/dbt-core", inferred from skill mentions even if not explicitly stated.'
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": raw_jd},
        ]

    def _call_llm(self, raw_jd: str) -> dict[str, Any]:
        settings = get_settings()
        if not settings.openrouter_api_key:
            return self._heuristic_parse(raw_jd).model_dump()
        payload = json.dumps(
            {
                "model": self.model,
                "messages": self._build_prompt(raw_jd),
                "temperature": 0,
            }
        ).encode("utf-8")
        req = urllib_request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=30) as response:
                content = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc
        message = content["choices"][0]["message"]["content"]
        return json.loads(message)

    def _heuristic_parse(self, raw_jd: str) -> JobDescription:
        lower = raw_jd.lower()
        company = "Unknown Company"
        role = "Unknown Role"
        match = re.search(r"(?P<role>.+?)\s+(at|for)\s+(?P<company>.+?)([.!\n]|$)", raw_jd, re.IGNORECASE)
        if match:
            role = match.group("role").strip().splitlines()[0][:80] or role
            company = match.group("company").strip().rstrip(".,")[:80] or company
        skills: list[str] = []
        repo_map = {
            "dbt": "dbt-labs/dbt-core",
            "airflow": "apache/airflow",
            "spark": "apache/spark",
            "llamaindex": "run-llama/llama_index",
            "kafka": "apache/kafka",
        }
        repos: list[str] = []
        for key, repo in repo_map.items():
            if key in lower:
                skills.append(key)
                repos.append(repo)
        languages = [lang for lang in ["python", "typescript", "javascript", "sql", "go", "rust"] if lang in lower]
        nice = [term.title() for term in ["dag", "etl", "data pipeline", "distributed systems"] if term in lower]
        years = 0
        for token in raw_jd.split():
            if token.isdigit():
                years = max(years, int(token))
        return JobDescription(
            company=company,
            role=role,
            required_skills=skills or ["open source contribution"],
            preferred_oss_repos=sorted(set(repos)),
            preferred_languages=languages or ["python"],
            experience_years_min=years or 0,
            nice_to_have=nice,
            raw_text=raw_jd,
        )

    def parse(self, raw_jd: str) -> JobDescription:
        """Parse a raw job description string into a JobDescription."""
        for attempt in range(2):
            try:
                payload = self._call_llm(raw_jd)
                return JobDescription.model_validate({**payload, "raw_text": raw_jd})
            except Exception:
                if attempt == 0:
                    continue
                raise
        raise RuntimeError("JD parsing failed")

    def to_coral_file(self, jd: JobDescription, output_path: str) -> None:
        """Write Coral-compatible JSON sources for JD repos and skills."""
        base = Path(output_path)
        repos_dir = base / "jd_requirements"
        repos_dir.mkdir(parents=True, exist_ok=True)
        repos_payload = [
            {
                "repo_name": repo,
                "importance": "required" if idx < max(1, len(jd.preferred_oss_repos)) else "preferred",
                "why_it_matters": f"Mapped from JD mention: {repo}",
            }
            for idx, repo in enumerate(jd.preferred_oss_repos or [f"{jd.company.lower()}/{jd.role.lower().replace(' ', '-') }"])
        ]
        skills_payload = [
            {"skill": skill, "category": "oss", "required": True}
            for skill in jd.required_skills
        ]
        (repos_dir / "repos.json").write_text(json.dumps(repos_payload, indent=2), encoding="utf-8")
        (repos_dir / "skills.json").write_text(json.dumps(skills_payload, indent=2), encoding="utf-8")
