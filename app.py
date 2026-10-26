import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# BrandGuard AI — Midnight Navy + Cyan UI
# Keeps the existing SQLite database and review workflow.
# ============================================================

st.set_page_config(
    page_title="BrandGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_NAME = "brandguard_history.db"

# -------------------------------
# Styling
# -------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
        --bg: #0b1220;
        --panel: #111c2e;
        --panel-2: #172438;
        --line: #293950;
        --text: #f1f5f9;
        --muted: #9fb0c5;
        --cyan: #67e8f9;
        --cyan-strong: #06b6d4;
        --green: #86efac;
        --amber: #fcd34d;
        --red: #fca5a5;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(ellipse at 10% 0%, rgba(8,145,178,.15), transparent 35%),
            linear-gradient(180deg, #0b1220 0%, #0a1020 100%);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(11,18,32,.75);
    }

    [data-testid="stSidebar"] {
        background: #0e192a;
        border-right: 1px solid var(--line);
    }

    [data-testid="stSidebar"] * {
        color: var(--text);
    }

    .block-container {
        max-width: 1240px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.025em;
        color: #f8fafc !important;
    }

    p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
        color: var(--text);
    }

    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #142238, #101a2b);
        border: 1px solid #2a3b52;
        padding: 18px 20px;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,.12);
    }

    [data-testid="stMetricLabel"] {
        color: #9fb0c5 !important;
    }

    [data-testid="stMetricValue"] {
        color: #67e8f9 !important;
        font-family: 'Space Grotesk', sans-serif;
    }

    .hero {
        background: linear-gradient(120deg, rgba(17,28,46,.98), rgba(18,47,66,.95));
        border: 1px solid #2b5267;
        border-radius: 22px;
        padding: 28px 30px;
        margin: 0 0 24px 0;
        box-shadow: 0 18px 45px rgba(0,0,0,.16);
    }

    .hero-kicker {
        color: #67e8f9;
        font-size: .76rem;
        font-weight: 700;
        letter-spacing: .16em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        color: #f8fafc;
        font-size: clamp(2rem, 4vw, 3rem);
        font-weight: 700;
        letter-spacing: -.05em;
        line-height: 1.1;
        margin: 0 0 10px 0;
    }

    .hero-copy {
        color: #c0d0e0;
        font-size: 1rem;
        max-width: 760px;
        line-height: 1.7;
        margin-bottom: 0;
    }

    .section-kicker {
        color: #67e8f9;
        font-size: .75rem;
        font-weight: 700;
        letter-spacing: .12em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .panel {
        background: rgba(17,28,46,.78);
        border: 1px solid #293950;
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 16px;
    }

    .status-pill {
        display: inline-block;
        border: 1px solid #34546b;
        background: #102a3a;
        color: #a5f3fc;
        border-radius: 999px;
        padding: 5px 11px;
        font-size: .78rem;
        font-weight: 700;
    }

    .muted {
        color: #9fb0c5;
        font-size: .9rem;
        line-height: 1.6;
    }

    div.stButton > button, div.stDownloadButton > button {
        border-radius: 10px;
        border: 1px solid #0891b2;
        font-weight: 700;
        min-height: 2.8rem;
        transition: all .15s ease;
    }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #0891b2, #06b6d4);
        color: #061521;
        border: none;
    }

    div.stButton > button:hover, div.stDownloadButton > button:hover {
        border-color: #67e8f9;
        color: #67e8f9;
    }

    textarea, input, [data-baseweb="select"] > div {
        background-color: #0e192a !important;
        border-color: #33465f !important;
        border-radius: 10px !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #293950;
        border-radius: 12px;
        overflow: hidden;
    }

    hr {
        border-color: #293950;
    }

    .small-note {
        color: #8ea2ba;
        font-size: .78rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------
# Database functions
# -------------------------------
def initialize_database():
    with sqlite3.connect(DB_NAME) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewed_at TEXT NOT NULL,
                content TEXT NOT NULL,
                compliance_score INTEGER NOT NULL,
                rules_checked INTEGER NOT NULL,
                issues_found INTEGER NOT NULL,
                risky_claims INTEGER NOT NULL,
                status TEXT NOT NULL,
                findings TEXT NOT NULL
            )
        """)


def save_review(
    content, score, rules_checked, issues_found,
    risky_claims, status, findings
):
    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_NAME) as connection:
        connection.execute("""
            INSERT INTO reviews (
                reviewed_at, content, compliance_score,
                rules_checked, issues_found, risky_claims,
                status, findings
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reviewed_at, content, score, rules_checked,
            issues_found, risky_claims, status, findings
        ))


def get_review_history():
    with sqlite3.connect(DB_NAME) as connection:
        return pd.read_sql_query("""
            SELECT
                id AS 'Review ID',
                reviewed_at AS 'Reviewed At',
                compliance_score AS 'Score (%)',
                rules_checked AS 'Rules Checked',
                issues_found AS 'Issues',
                risky_claims AS 'Risky Claims',
                status AS 'Status'
            FROM reviews
            ORDER BY id DESC
        """, connection)


def get_review_details(review_id):
    with sqlite3.connect(DB_NAME) as connection:
        cursor = connection.execute("""
            SELECT content, findings
            FROM reviews
            WHERE id = ?
        """, (review_id,))
        return cursor.fetchone()


# -------------------------------
# Review helper functions
# -------------------------------
def contains_phrase(text, phrase):
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return bool(re.search(pattern, text, re.IGNORECASE))


def parse_phrases(text):
    return [phrase.strip() for phrase in text.split(",") if phrase.strip()]


def run_review(content, prohibited_phrases, required_phrases):
    issues = []
    total_rules = 0
    passed_rules = 0

    for phrase in prohibited_phrases:
        total_rules += 1
        if contains_phrase(content, phrase):
            issues.append({
                "Type": "Prohibited phrase",
                "Phrase": phrase,
                "Severity": "High",
                "Finding": f"Prohibited phrase detected: '{phrase}'.",
                "Suggestion": (
                    f"Remove '{phrase}' or replace it with a specific, "
                    "supportable statement."
                ),
            })
        else:
            passed_rules += 1

    for phrase in required_phrases:
        total_rules += 1
        if contains_phrase(content, phrase):
            passed_rules += 1
        else:
            issues.append({
                "Type": "Missing required phrase",
                "Phrase": phrase,
                "Severity": "Medium",
                "Finding": f"Required phrase is missing: '{phrase}'.",
                "Suggestion": (
                    f"Include '{phrase}' naturally if appropriate for the content."
                ),
            })

    score = 100 if total_rules == 0 else round((passed_rules / total_rules) * 100)

    # These are phrase-based warning patterns, not proof that a claim is false.
    # Keep the list explicit and explain to reviewers why each phrase may need evidence.
    risky_phrases = [
        "best in the world",
        "number one",
        "no. 1",
        "100% effective",
        "100% of customers",
        "works for 100% of customers",
        "works for everyone",
        "guaranteed results",
        "guaranteed to work",
        "guarantees a complete cure",
        "complete cure",
        "cure for acne",
        "cure all",
        "clinically proven",
        "scientifically proven",
        "instant results",
        "in just 24 hours",
        "within 24 hours",
        "results in 24 hours",
        "permanent results",
        "zero side effects",
        "risk-free",
        "zero effort",
    ]
    detected_risks = [
        phrase for phrase in risky_phrases if contains_phrase(content, phrase)
    ]

    status = "NEEDS REVIEW" if issues or detected_risks else "PASS"

    finding_lines = []
    for issue in issues:
        finding_lines.append(
            f"{issue['Severity']}: {issue['Finding']} "
            f"Suggestion: {issue['Suggestion']}"
        )

    if not issues:
        finding_lines.append("No configured rule violations detected.")

    if detected_risks:
        finding_lines.append(
            "Risky claims flagged for human review: " + ", ".join(detected_risks)
        )

    findings_text = "\n".join(finding_lines)

    report_lines = [
        "BrandGuard AI - Compliance Review Report",
        "=" * 45,
        f"Review Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Compliance Score: {score}%",
        f"Rules Checked: {total_rules}",
        f"Issues Found: {len(issues)}",
        f"Risky Claims Flagged: {len(detected_risks)}",
        f"Status: {status}",
        "",
        "Original Marketing Content:",
        content,
        "",
        "Findings and Suggestions:",
        findings_text,
        "",
        "Note: This is a rule-based prototype. Human review is required "
        "for context, factual accuracy, and final approval.",
    ]

    return {
        "score": score,
        "total_rules": total_rules,
        "passed_rules": passed_rules,
        "issues": issues,
        "detected_risks": detected_risks,
        "status": status,
        "findings_text": findings_text,
        "report": "\n".join(report_lines),
    }


initialize_database()


# -------------------------------
# Sidebar
# -------------------------------
with st.sidebar:
    st.markdown("## 🛡️ BrandGuard AI")
    st.caption("BRAND INTELLIGENCE")
    st.divider()
    page = st.radio(
        "Workspace",
        ["Content Review", "Review History", "About BrandGuard"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Review engine**")
    st.markdown(
        '<span class="status-pill">Rule-based prototype</span>',
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        '<p class="muted">Built to help teams spot configured brand-rule '
        'violations and claims that need human attention.</p>',
        unsafe_allow_html=True,
    )
    st.caption("BrandGuard AI • Round 2 build")


# -------------------------------
# Hero header
# -------------------------------
st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">Brand intelligence platform</div>
      <div class="hero-title">Protect your brand voice.</div>
      <p class="hero-copy">
        Review marketing content against configured guidelines, flag potentially
        exaggerated claims, and keep a traceable history of your reviews.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "latest_report" not in st.session_state:
    st.session_state["latest_report"] = None
if "latest_result" not in st.session_state:
    st.session_state["latest_result"] = None


# -------------------------------
# Content Review page
# -------------------------------
if page == "Content Review":
    st.markdown('<div class="section-kicker">01 / Brand policy</div>', unsafe_allow_html=True)
    st.header("Configure your guidelines")
    st.markdown(
        '<p class="muted">Set the phrases to avoid and the terms that must appear '
        'in your marketing copy.</p>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        prohibited_input = st.text_area(
            "Prohibited words or phrases",
            value="guaranteed, 100% risk-free",
            help="Separate phrases with commas.",
            height=105,
        )
    with right:
        required_input = st.text_area(
            "Required words or phrases",
            value="BrandGuard",
            help="Separate phrases with commas.",
            height=105,
        )

    st.divider()
    st.markdown('<div class="section-kicker">02 / Content workspace</div>', unsafe_allow_html=True)
    st.header("Review marketing content")
    st.markdown(
        '<p class="muted">Paste your draft below. BrandGuard AI will check your '
        'configured phrase rules and flag selected claims for human review.</p>',
        unsafe_allow_html=True,
    )

    with st.form("brandguard_review_form", clear_on_submit=False):
        draft = st.text_area(
            "Marketing draft",
            height=220,
            placeholder="Example: BrandGuard helps teams review marketing content...",
            label_visibility="visible",
        )
        submitted = st.form_submit_button(
            "🛡️  Run compliance check",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not draft.strip():
            st.warning("Please enter some marketing content before running a review.")
        else:
            result = run_review(
                draft,
                parse_phrases(prohibited_input),
                parse_phrases(required_input),
            )
            save_review(
                content=draft,
                score=result["score"],
                rules_checked=result["total_rules"],
                issues_found=len(result["issues"]),
                risky_claims=len(result["detected_risks"]),
                status=result["status"],
                findings=result["findings_text"],
            )
            st.session_state["latest_result"] = result
            st.session_state["latest_report"] = result["report"]
            st.session_state["latest_content"] = draft
            st.session_state["latest_review_time"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            st.success("Review completed and saved to your local review history.")

    result = st.session_state.get("latest_result")
    if result:
        st.divider()
        st.markdown('<div class="section-kicker">03 / Analysis</div>', unsafe_allow_html=True)
        st.header("Review overview")

        metric_cols = st.columns(4, gap="medium")
        metric_cols[0].metric("Compliance score", f'{result["score"]}%')
        metric_cols[1].metric("Rules checked", result["total_rules"])
        metric_cols[2].metric("Rule issues", len(result["issues"]))
        metric_cols[3].metric("Risk flags", len(result["detected_risks"]))

        if result["status"] == "PASS":
            st.success("PASS — No configured rule violations or listed risky claims detected.")
        else:
            st.warning("NEEDS REVIEW — Inspect the findings and risky-claim flags before approval.")

        st.progress(result["score"] / 100)
        st.caption(
            "Score is based only on configured required/prohibited phrase rules. "
            "Risky-claim flags are separate and do not change the score."
        )

        issue_tab, risk_tab, report_tab = st.tabs(
            ["Rule findings", "Risky claims", "Download report"]
        )

        with issue_tab:
            if result["issues"]:
                for issue in result["issues"]:
                    with st.container(border=True):
                        badge_color = "🔴" if issue["Severity"] == "High" else "🟠"
                        st.markdown(
                            f"### {badge_color} {issue['Type']} · {issue['Severity']}"
                        )
                        st.write(issue["Finding"])
                        st.markdown("**Suggested correction**")
                        st.write(issue["Suggestion"])
            else:
                st.success("No configured prohibited or missing-phrase issues found.")

        with risk_tab:
            if result["detected_risks"]:
                st.warning(
                    "Potentially risky wording was detected. These flags are prompts for "
                    "evidence checks and human review; they do not prove a claim is false."
                )
                risk_guidance = {
                    "best in the world": "Superlative claim: provide reliable, current evidence and define the comparison.",
                    "number one": "Ranking claim: provide a credible source, market, category, and date for the ranking.",
                    "no. 1": "Ranking claim: provide a credible source, market, category, and date for the ranking.",
                    "100% effective": "Absolute effectiveness claim: require strong evidence that supports the exact percentage and context.",
                    "100% of customers": "Universal customer-outcome claim: verify the sample, methodology, and supporting data.",
                    "works for 100% of customers": "Universal customer-outcome claim: verify the sample, methodology, and supporting data.",
                    "works for everyone": "Absolute claim: check whether reliable evidence supports the statement for all users.",
                    "guaranteed results": "Guarantee claim: clarify the guarantee terms and verify that the promise can be honored.",
                    "guaranteed to work": "Guarantee claim: clarify the conditions and provide evidence for the promised outcome.",
                    "guarantees a complete cure": "Medical outcome claim: requires careful substantiation and qualified human/regulatory review.",
                    "complete cure": "Medical outcome claim: requires careful substantiation and qualified human/regulatory review.",
                    "cure for acne": "Medical treatment claim: check approved evidence and applicable advertising rules before publication.",
                    "cure all": "Absolute cure claim: requires strong substantiation and qualified human/regulatory review.",
                    "clinically proven": "Evidence claim: identify the clinical study and confirm that it supports this exact product and claim.",
                    "scientifically proven": "Evidence claim: identify credible research and confirm that it supports this exact statement.",
                    "instant results": "Speed-of-results claim: provide evidence for the stated timeframe and conditions.",
                    "in just 24 hours": "Specific timeframe claim: provide evidence that supports this result within the stated timeframe.",
                    "within 24 hours": "Specific timeframe claim: provide evidence that supports this result within the stated timeframe.",
                    "results in 24 hours": "Specific timeframe claim: provide evidence that supports this result within the stated timeframe.",
                    "permanent results": "Long-term outcome claim: provide evidence for the duration and conditions implied.",
                    "zero side effects": "Absolute safety claim: avoid implying risk is impossible; require qualified review and reliable evidence.",
                    "risk-free": "Absolute safety claim: check whether the statement misleadingly implies no risk.",
                    "zero effort": "Effort-free promise: check whether the statement creates an unrealistic or misleading expectation.",
                }
                for phrase in result["detected_risks"]:
                    with st.container(border=True):
                        st.markdown(f"**⚠️ {phrase}**")
                        st.write(risk_guidance.get(
                            phrase,
                            "Review this wording and verify that reliable evidence supports the exact claim."
                        ))
                        st.caption("Suggested action: verify the evidence, narrow the wording if needed, and obtain human approval.")
            else:
                st.success("No phrases from the prototype risk list were detected. This does not guarantee factual accuracy or full compliance.")

        with report_tab:
            st.markdown(
                '<p class="muted">Download a text report containing the score, '
                'content, findings, and suggested corrections.</p>',
                unsafe_allow_html=True,
            )
            st.download_button(
                "⬇️ Download review report",
                data=st.session_state["latest_report"],
                file_name="brandguard_review_report.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with st.expander("View original content"):
            st.code(st.session_state.get("latest_content", ""), language=None)

    st.divider()
    st.markdown(
        '<p class="small-note">BrandGuard AI is a rule-based prototype. '
        'It does not independently verify factual accuracy or guarantee complete compliance. '
        'Human review is required before publication.</p>',
        unsafe_allow_html=True,
    )


# -------------------------------
# Review History page
# -------------------------------
elif page == "Review History":
    st.markdown('<div class="section-kicker">04 / Audit trail</div>', unsafe_allow_html=True)
    st.header("Review history")
    st.markdown(
        '<p class="muted">Browse saved reviews stored in your local SQLite database. '
        'History remains available after restarting while the database file is preserved.</p>',
        unsafe_allow_html=True,
    )

    history = get_review_history()
    if history.empty:
        st.info("No reviews saved yet. Run a content review to create your first history record.")
    else:
        total_reviews = len(history)
        avg_score = round(float(history["Score (%)"].mean()))
        total_issues = int(history["Issues"].sum())
        h1, h2, h3 = st.columns(3)
        h1.metric("Saved reviews", total_reviews)
        h2.metric("Average score", f"{avg_score}%")
        h3.metric("Recorded rule issues", total_issues)

        st.dataframe(history, use_container_width=True, hide_index=True)

        st.markdown("### Inspect a saved review")
        review_ids = history["Review ID"].tolist()
        selected_id = st.selectbox(
            "Choose a review",
            options=review_ids,
            format_func=lambda review_id: (
                f"Review #{review_id} — "
                + history.loc[
                    history["Review ID"] == review_id, "Reviewed At"
                ].iloc[0]
            ),
        )
        details = get_review_details(selected_id)
        if details:
            with st.container(border=True):
                st.markdown("**Original marketing content**")
                st.code(details[0], language=None)
                st.markdown("**Review findings**")
                st.text(details[1])


# -------------------------------
# About page
# -------------------------------
else:
    st.markdown('<div class="section-kicker">05 / Product information</div>', unsafe_allow_html=True)
    st.header("About BrandGuard AI")
    st.markdown(
        """
        BrandGuard AI is a prototype for reviewing marketing copy against
        configurable brand phrase rules.

        **Current capabilities**
        - Prohibited-phrase detection
        - Required-phrase checks
        - Rule-based compliance scoring
        - Suggested corrections for detected rule issues
        - Expanded risky-claim phrase checks with explanations and suggested review actions
        - Downloadable review reports
        - Persistent review history using SQLite

        **Technology**
        - Python and Streamlit for the application interface
        - Regular expressions for phrase matching
        - SQLite for saved review records
        - Pandas for review-history display

        **Known limitations**
        - The app uses configured phrase rules rather than a trained AI model.
        - Risky-claim flags identify phrases for review; they do not prove claims are false.
        - The score does not establish factual accuracy or complete brand compliance.
        - The database is stored locally alongside the app and is not a shared multi-user database.
        """
    )

st.divider()
st.caption("🛡️ BrandGuard AI  ·  Midnight Navy + Cyan  ·  Rule-based prototype")
