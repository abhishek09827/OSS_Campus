"""Tests for the JD parser."""

from __future__ import annotations

import json
from pathlib import Path

from app.jd_parser.parser import JDParser


def test_parse_extracts_repos_from_realistic_jd():
    """Heuristic parsing should infer OSS repos from a dbt Labs JD."""
    raw = """
    Senior Data Engineer at dbt Labs.
    Must have experience with dbt, Airflow, and Python.
    Nice to have Spark and LlamaIndex familiarity.
    """
    parser = JDParser()
    jd = parser.parse(raw)
    assert jd.company == "dbt Labs"
    assert "dbt-labs/dbt-core" in jd.preferred_oss_repos
    assert "apache/airflow" in jd.preferred_oss_repos
    assert "run-llama/llama_index" in jd.preferred_oss_repos


def test_to_coral_file_writes_json(tmp_path):
    """The Coral file source output should be valid JSON files."""
    parser = JDParser()
    jd = parser._heuristic_parse("Data Engineer at dbt Labs with dbt and python.")
    parser.to_coral_file(jd, str(tmp_path))
    repos_path = tmp_path / "jd_requirements" / "repos.json"
    skills_path = tmp_path / "jd_requirements" / "skills.json"
    assert repos_path.exists()
    assert skills_path.exists()
    repos = json.loads(repos_path.read_text(encoding="utf-8"))
    skills = json.loads(skills_path.read_text(encoding="utf-8"))
    assert isinstance(repos, list) and repos
    assert isinstance(skills, list) and skills


def test_minimal_jd_parses():
    """A minimal JD should still return a usable structure."""
    parser = JDParser()
    jd = parser.parse("Platform Engineer at Company X.")
    assert jd.company == "Company X"
    assert jd.role
