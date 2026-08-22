"""
ui_components.py
------------------
All Streamlit rendering / styling helpers live here, kept deliberately
separate from the medical classification logic (src/classifier.py) and
from the medical knowledge configuration (data/lab_tests.json).

This module is the only place that should contain HTML/CSS or direct
`st.markdown(..., unsafe_allow_html=True)` calls for styled components,
so the visual language of the app stays in one place.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.models import ClassifiedLabResult
from src.summary import PatientSummary

STATUS_LABELS = {
    "normal": "תקין",
    "borderline": "גבולי",
    "abnormal": "חריג",
}

STATUS_ICONS = {
    "normal": "🟢",
    "borderline": "🟡",
    "abnormal": "🔴",
}


# ---------------------------------------------------------------------------
# Global styling
# ---------------------------------------------------------------------------

def inject_global_css() -> None:
    """Inject the global RTL / healthcare visual identity once per page."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;700;800&family=Assistant:wght@400;500;600;700&display=swap');

        :root {
            --me-bg: #EAF6F6;
            --me-bg-alt: #DCF1EF;
            --me-card: #FFFFFF;
            --me-border: #D9EEEC;
            --me-accent: #1E9E96;
            --me-accent-dark: #12746E;
            --me-text: #1F2D3D;
            --me-text-secondary: #5B6B79;
            --me-shadow: rgba(18, 116, 110, 0.10);
            --me-green-bg: #E5F6EC; --me-green-text: #1E7A46; --me-green-dot: #34A853;
            --me-yellow-bg: #FFF6DF; --me-yellow-text: #8A6D1B; --me-yellow-dot: #E8A93B;
            --me-red-bg: #FDEBEA; --me-red-text: #B3261E; --me-red-dot: #E5484D;
        }

        html, body, [class*="css"] {
            direction: rtl;
            font-family: 'Assistant', 'Heebo', sans-serif;
        }

        .stApp {
            background: linear-gradient(180deg, var(--me-bg) 0%, var(--me-bg-alt) 100%);
        }

        h1, h2, h3, h4 {
            font-family: 'Heebo', sans-serif;
            color: var(--me-text);
            text-align: right;
        }

        p, span, div, label, li {
            text-align: right;
        }

        section[data-testid="stSidebar"] {
            background-color: #F4FBFA;
            border-left: 1px solid var(--me-border);
        }

        section[data-testid="stSidebar"] * {
            text-align: right;
        }

        .me-app-title {
            font-family: 'Heebo', sans-serif;
            font-weight: 800;
            font-size: 1.55rem;
            color: var(--me-accent-dark);
            margin-bottom: 0.1rem;
        }

        .me-app-subtitle {
            color: var(--me-text-secondary);
            font-size: 0.95rem;
            margin-bottom: 1.2rem;
        }

        .me-card {
            background: var(--me-card);
            border: 1px solid var(--me-border);
            border-radius: 18px;
            padding: 1.4rem 1.6rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 4px 18px var(--me-shadow);
        }

        .me-card h4 {
            margin-top: 0;
            margin-bottom: 0.6rem;
            font-size: 1.05rem;
            color: var(--me-accent-dark);
        }

        .me-section-label {
            font-weight: 700;
            font-size: 0.92rem;
            color: var(--me-accent-dark);
            margin-top: 0.9rem;
            margin-bottom: 0.3rem;
        }

        .me-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.85rem;
        }

        .me-badge-normal { background: var(--me-green-bg); color: var(--me-green-text); }
        .me-badge-borderline { background: var(--me-yellow-bg); color: var(--me-yellow-text); }
        .me-badge-abnormal { background: var(--me-red-bg); color: var(--me-red-text); }

        .me-trend {
            font-size: 0.82rem;
            color: var(--me-text-secondary);
            margin-right: 0.4rem;
        }

        .me-disclaimer {
            background: #FFF9EC;
            border: 1px solid #F3E3B8;
            border-radius: 14px;
            padding: 0.9rem 1.2rem;
            color: #6B5A22;
            font-size: 0.88rem;
            margin-bottom: 1rem;
        }

        .me-question-item {
            background: #F4FBFA;
            border-radius: 12px;
            padding: 0.55rem 0.9rem;
            margin-bottom: 0.45rem;
            color: var(--me-text);
            font-size: 0.94rem;
        }

        table.me-results-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 8px;
        }

        table.me-results-table th {
            text-align: right;
            font-size: 0.82rem;
            color: var(--me-text-secondary);
            font-weight: 600;
            padding: 0 0.9rem;
        }

        table.me-results-table td {
            background: var(--me-card);
            padding: 0.85rem 0.9rem;
            font-size: 0.95rem;
            color: var(--me-text);
            border-top: 1px solid var(--me-border);
            border-bottom: 1px solid var(--me-border);
        }

        table.me-results-table tr td:first-child {
            border-radius: 0 14px 14px 0;
            border-right: 1px solid var(--me-border);
        }

        table.me-results-table tr td:last-child {
            border-radius: 14px 0 0 14px;
            border-left: 1px solid var(--me-border);
        }

        .me-flow-step {
            background: var(--me-card);
            border: 1px solid var(--me-border);
            border-radius: 14px;
            padding: 0.75rem 1rem;
            text-align: center;
            font-weight: 600;
            color: var(--me-accent-dark);
            box-shadow: 0 2px 10px var(--me-shadow);
        }

        .me-flow-arrow {
            text-align: center;
            color: var(--me-accent);
            font-size: 1.3rem;
            line-height: 1.3rem;
        }

        .me-summary-counts {
            display: flex;
            gap: 0.9rem;
            flex-wrap: wrap;
            margin-bottom: 0.8rem;
        }

        .me-count-pill {
            border-radius: 14px;
            padding: 0.6rem 1rem;
            font-weight: 700;
            font-size: 0.95rem;
            min-width: 90px;
            text-align: center;
        }

        div[data-testid="stMetric"] {
            background: var(--me-card);
            border: 1px solid var(--me-border);
            border-radius: 16px;
            padding: 0.8rem 1rem;
            box-shadow: 0 2px 10px var(--me-shadow);
        }

        .stButton>button {
            border-radius: 12px;
            font-weight: 700;
            background: var(--me-accent);
            color: white;
            border: none;
        }
        .stButton>button:hover {
            background: var(--me-accent-dark);
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(title: str, subtitle: str = "") -> None:
    subtitle_html = f'<div class="me-app-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="me-app-title">{title}</div>{subtitle_html}',
        unsafe_allow_html=True,
    )


def render_disclaimer(text: str) -> None:
    st.markdown(f'<div class="me-disclaimer">⚠️ {text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Results table
# ---------------------------------------------------------------------------

def results_to_dataframe(results: list[ClassifiedLabResult]) -> pd.DataFrame:
    """Build a tidy Pandas DataFrame for display of classified lab results."""
    rows = []
    for r in results:
        rows.append(
            {
                "בדיקה": f"{r.name_he} ({r.abbreviation})",
                "תוצאה": r.value,
                "יחידות": r.unit,
                "טווח ייחוס": r.reference_text,
                "סטטוס": STATUS_LABELS.get(r.status, r.status),
                "_status_key": r.status,
                "_trend": r.trend,
            }
        )
    return pd.DataFrame(rows)


def render_results_table(results: list[ClassifiedLabResult]) -> None:
    """Render the lab results as a styled, calm (non-dense) HTML table."""
    if not results:
        st.info("לא הוזנו תוצאות בדיקה להצגה.")
        return

    df = results_to_dataframe(results)

    rows_html = ""
    for _, row in df.iterrows():
        badge_class = f"me-badge-{row['_status_key']}"
        icon = STATUS_ICONS.get(row["_status_key"], "")
        trend_html = ""
        if row["_trend"] == "up":
            trend_html = '<span class="me-trend">↑ עלה</span>'
        elif row["_trend"] == "down":
            trend_html = '<span class="me-trend">↓ ירד</span>'
        rows_html += (
            "<tr>"
            f"<td>{row['בדיקה']}</td>"
            f"<td>{row['תוצאה']}{trend_html}</td>"
            f"<td>{row['יחידות']}</td>"
            f"<td>{row['טווח ייחוס']}</td>"
            f"<td><span class='me-badge {badge_class}'>{icon} {row['סטטוס']}</span></td>"
            "</tr>"
        )

    table_html = f"""
    <table class="me-results-table">
        <thead>
            <tr>
                <th>בדיקה</th><th>תוצאה</th><th>יחידות</th><th>טווח ייחוס</th><th>סטטוס</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Explanation cards
# ---------------------------------------------------------------------------

def render_explanation_card(explanation: dict, questions: list[str] | None) -> None:
    """Render one full explanation card for a borderline/abnormal result."""
    badge_class = f"me-badge-{explanation['status']}"
    icon = STATUS_ICONS.get(explanation["status"], "")
    label = STATUS_LABELS.get(explanation["status"], explanation["status"])

    reasons_html = ""
    if explanation["possible_reasons"]:
        items = "".join(f"<li>{reason}</li>" for reason in explanation["possible_reasons"])
        reasons_html = f"<ul>{items}</ul>"
    else:
        reasons_html = "<p>אין מידע נוסף זמין עבור כיוון סטייה זה באב-הטיפוס.</p>"

    questions_html = ""
    if questions:
        q_items = "".join(f'<div class="me-question-item">🩺 {q}</div>' for q in questions)
        questions_html = q_items

    st.markdown(
        f"""
        <div class="me-card">
            <h4>{explanation['name_he']} &nbsp;
                <span class="me-badge {badge_class}">{icon} {label}</span>
            </h4>
            <div class="me-section-label">סיכום קצר</div>
            <p>{explanation['summary']}</p>

            <div class="me-section-label">מה הבדיקה מודדת?</div>
            <p>{explanation['what_it_measures']}</p>

            <div class="me-section-label">מה יכול להשפיע על הערך?</div>
            {reasons_html}

            <div class="me-section-label">כמה זה דחוף?</div>
            <p>{explanation['urgency_text']}</p>

            <div class="me-section-label">למי נכון לפנות?</div>
            <p>{explanation['who_to_consult']}</p>

            <div class="me-section-label">מה כדאי לשאול את הרופא?</div>
            {questions_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Summary card
# ---------------------------------------------------------------------------

def render_summary_card(summary: PatientSummary) -> None:
    st.markdown(
        f"""
        <div class="me-summary-counts">
            <div class="me-count-pill" style="background: var(--me-green-bg); color: var(--me-green-text);">
                🟢 תקין: {summary.normal_count}
            </div>
            <div class="me-count-pill" style="background: var(--me-yellow-bg); color: var(--me-yellow-text);">
                🟡 גבולי: {summary.borderline_count}
            </div>
            <div class="me-count-pill" style="background: var(--me-red-bg); color: var(--me-red-text);">
                🔴 חריג: {summary.abnormal_count}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="me-card"><p>{summary.headline}</p></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Architecture flow diagram (simple, no raw framework needed)
# ---------------------------------------------------------------------------

def render_architecture_flow(steps: list[str]) -> None:
    for i, step in enumerate(steps):
        st.markdown(f'<div class="me-flow-step">{step}</div>', unsafe_allow_html=True)
        if i < len(steps) - 1:
            st.markdown('<div class="me-flow-arrow">↓</div>', unsafe_allow_html=True)
