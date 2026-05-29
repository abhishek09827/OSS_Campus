"""Streamlit UI for OSS Compass."""

from __future__ import annotations

import json
from typing import Any
import pandas as pd
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from app._compat import get_streamlit


st = get_streamlit()
API_BASE = "http://localhost:8000"


def _score_color(score: int) -> str:
    if score <= 40:
        return "#c0392b"
    if score <= 60:
        return "#e67e22"
    if score <= 80:
        return "#2ecc71"
    return "#2980b9"


def _fetch_history(username: str) -> list[dict[str, Any]]:
    try:
        with urllib_request.urlopen(f"{API_BASE}/history/{urllib_parse.quote(username)}", timeout=10) as response:
            return json.loads(response.read().decode("utf-8")).get("items", [])
    except Exception:
        return []


def _analyse(username: str, jd_text: str) -> dict[str, Any] | None:
    try:
        payload = json.dumps({"github_username": username, "jd_text": jd_text}).encode("utf-8")
        req = urllib_request.Request(
            f"{API_BASE}/analyse",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=60) as response:
            report = None
            for raw_line in response.read().decode("utf-8").splitlines():
                if not raw_line:
                    continue
                payload = json.loads(raw_line)
                if "report" in payload:
                    report = payload["report"]
            return report
    except Exception:
        return None


def main() -> None:
    """Render the Streamlit app."""
    st.set_page_config(page_title="OSS Compass", layout="wide")
    left, middle, right = st.columns(3)

    with left:
        st.header("Input")
        username = st.text_input("GitHub username")
        jd_text = st.text_area("Paste job description", height=300)
        analyse_clicked = st.button("Analyse")
        with st.expander("View past analyses"):
            for item in _fetch_history(username) if username else []:
                st.write(f"{item.get('target_company')} - {item.get('readiness_label')} ({item.get('readiness_score')})")

    report = None
    if analyse_clicked and username and jd_text:
        with st.status("Running analysis...") as status:
            status.update(label="Parsing job description")
            report = _analyse(username, jd_text)
            status.update(label="Complete")

    if report:
        score = int(report["readiness_score"])
        color = _score_color(score)
        with middle:
            st.markdown(
                f"<h1 style='color:{color}; margin-bottom:0'>{score}</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(f"<h3 style='color:{color}'>{report['readiness_label']}</h3>", unsafe_allow_html=True)
            st.write(report["summary"])
            with st.expander("Strengths"):
                for item in report["strengths"]:
                    st.write(f"- {item}")
            with st.expander("Gaps"):
                for item in report["gaps"]:
                    st.write(f"- {item}")
            st.dataframe(pd.DataFrame([report["breakdown"]]))

        with right:
            st.subheader("Your Next 3 Contributions")
            for item in report["next_contributions"]:
                st.markdown(f"**{item['repo']}**")
                st.markdown(f"[{item['issue_title']}]({item['issue_url']})")
                st.caption(f"*{item['why_this_one']}*")
                st.write(f"Estimated days: {item['estimated_days']} | +{item['score_impact']} points")
            try:
                with urllib_request.urlopen(
                    f"{API_BASE}/similar?summary={urllib_parse.quote(report['summary'])}",
                    timeout=10,
                ) as response:
                    traj = json.loads(response.read().decode("utf-8")).get("items", [])
                if traj:
                    df = pd.DataFrame(
                        [{"month": idx, "merged_prs": len(item.get("next_contributions", []))} for idx, item in enumerate(traj)]
                    )
                    if not df.empty:
                        st.line_chart(df.set_index("month"))
            except Exception:
                pass
    elif analyse_clicked:
        st.error("Analysis failed. Make sure the FastAPI backend is running on localhost:8000.")


if __name__ == "__main__":
    main()
