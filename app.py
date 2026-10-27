
import re
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

# ============================================================
# BrandGuard AI — Round 3
# Content Review + Evidence Verification + Review History
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
        --line: #293950;
        --text: #f1f5f9;
        --muted: #9fb0c5;
        --cyan: #67e8f9;
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
        color: #f8fafc !important;
    }

    p, label, .stMarkdown {
        color: var(--text);
    }

    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #142238, #101a2b);
        border: 1px solid #2a3b52;
        padding: 18px;
        border-radius: 16px;
    }

    [data-testid="stMetricLabel"] {
        color: #9fb0c5 !important;
    }

    [data-testid="stMetricValue"] {
        color: #67e8f9 !important;
        font-family: 'Space Grotesk', sans-serif;
    }

    .hero {
        background: linear-gradient(120deg, #111c2e, #122f42);
        border: 1px solid #2b5267;
        border-radius: 22px;
        padding: 28px 30px;
        margin-bottom: 24px;
    }

    .hero-kicker, .section-kicker {
        color: #67e8f9;
        font-size: .76rem;
        font-weight: 700;
        letter-spacing: .13em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        color: #f8fafc;
        font-size: clamp(2rem, 4vw, 3rem);
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 12px;
    }

    .hero-copy, .muted {
        color: #b9c9dc;
        line-height: 1.7;
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

    div.stButton > button, div.stDownloadButton > button {
        border-radius: 10px;
        border: 1px solid #0891b2;
        font-weight: 700;
        min-height: 2.7rem;
    }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #0891b2, #06b6d4);
        color: #061521;
        border: none;
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
        font-size: .8rem;
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


RISK_GUIDANCE = {
    "best in the world":
        "Superlative claim: define the comparison and provide reliable evidence.",
    "number one":
        "Ranking claim: verify the source, category, market, and date.",
    "no. 1":
        "Ranking claim: verify the source, category, market, and date.",
    "100% effective":
        "Absolute effectiveness claim: substantiate the exact percentage and context.",
    "100% of customers":
        "Universal customer-outcome claim: verify the data and methodology.",
    "works for 100% of customers":
        "Universal customer-outcome claim: verify the data and methodology.",
    "works for everyone":
        "Absolute claim: check whether reliable evidence supports the statement.",
    "guaranteed results":
        "Clarify the guarantee terms and verify that the promise can be honored.",
    "guaranteed to work":
        "Check the conditions and evidence for the promised outcome.",
    "guarantees a complete cure":
        "Medical outcome claim: requires substantiation and qualified review.",
    "complete cure":
        "Medical outcome claim: requires substantiation and qualified review.",
    "cure for acne":
        "Check appropriate medical evidence and applicable advertising rules.",
    "cure all":
        "Absolute cure claim: requires substantiation and qualified review.",
    "clinically proven":
        "Identify the clinical study and verify it supports this exact product and claim.",
    "scientifically proven":
        "Identify credible research supporting the exact statement.",
    "instant results":
        "Provide evidence for the stated speed and conditions.",
    "in just 24 hours":
        "Verify evidence supports the stated timeframe.",
    "within 24 hours":
        "Verify evidence supports the stated timeframe.",
    "results in 24 hours":
        "Verify evidence supports the stated timeframe.",
    "permanent results":
        "Provide evidence for the implied duration and conditions.",
    "zero side effects":
        "Absolute safety claim: qualified review and reliable evidence are needed.",
    "risk-free":
        "Check whether the wording misleadingly implies no risk.",
    "zero effort":
        "Check whether the wording creates an unrealistic expectation.",
}


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
                    f"Include '{phrase}' naturally if appropriate."
                ),
            })

    score = (
        100 if total_rules == 0
        else round((passed_rules / total_rules) * 100)
    )

    detected_risks = [
        phrase for phrase in RISK_GUIDANCE
        if contains_phrase(content, phrase)
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
            "Risky claims flagged for human review: "
            + ", ".join(detected_risks)
        )

    findings_text = "\n".join(finding_lines)

    report = "\n".join([
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
    ])

    return {
        "score": score,
        "total_rules": total_rules,
        "passed_rules": passed_rules,
        "issues": issues,
        "detected_risks": detected_risks,
        "status": status,
        "findings_text": findings_text,
        "report": report,
    }


# -------------------------------
# Evidence comparison helper
# -------------------------------
def get_terms(text):
    cleaned_words = re.findall(r"\b[a-zA-Z0-9'-]+\b", text.lower())

    # Ignore common words that usually provide little useful comparison.
    stop_words = {
        "the", "and", "for", "with", "this", "that", "from",
        "have", "has", "had", "are", "was", "were", "our",
        "your", "their", "they", "them", "into", "after",
        "before", "within", "which", "will", "would", "could",
        "should", "about", "been", "being", "than", "then",
    }

    return {
        word for word in cleaned_words
        if len(word) > 3 and word not in stop_words
    }


# -------------------------------
# Initialize app state and database
# -------------------------------
initialize_database()

if "latest_result" not in st.session_state:
    st.session_state["latest_result"] = None

if "latest_report" not in st.session_state:
    st.session_state["latest_report"] = None

if "latest_content" not in st.session_state:
    st.session_state["latest_content"] = ""


# -------------------------------
# Sidebar
# -------------------------------
with st.sidebar:
    st.markdown("## 🛡️ BrandGuard AI")
    st.caption("BRAND INTELLIGENCE")
    st.divider()

    page = st.radio(
        "Workspace",
        [
            "Content Review",
            "Review History",
            "Evidence Verification",
            "About BrandGuard",
        ],
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
        '<p class="muted">Find configured brand-rule violations '
        'and claims that need human attention.</p>',
        unsafe_allow_html=True,
    )
    st.caption("BrandGuard AI • Round 3 build")


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
        exaggerated claims, compare claim wording with supplied evidence, and
        keep a traceable history of your reviews.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PAGE 1 — CONTENT REVIEW
# ============================================================
if page == "Content Review":

    st.markdown(
        '<div class="section-kicker">01 / Brand policy</div>',
        unsafe_allow_html=True,
    )
    st.header("Configure your guidelines")
    st.markdown(
        '<p class="muted">Set phrases to avoid and terms that must appear '
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
            key="prohibited_input",
        )

    with right:
        required_input = st.text_area(
            "Required words or phrases",
            value="BrandGuard",
            help="Separate phrases with commas.",
            height=105,
            key="required_input",
        )

    st.divider()
    st.markdown(
        '<div class="section-kicker">02 / Content workspace</div>',
        unsafe_allow_html=True,
    )
    st.header("Review marketing content")
    st.write(
        "Check configured phrase rules and flag selected claims "
        "for human review."
    )

    with st.form("brandguard_review_form", clear_on_submit=False):
        draft = st.text_area(
            "Marketing draft",
            height=220,
            placeholder=(
                "Example: BrandGuard helps teams review marketing content..."
            ),
        )

        submitted = st.form_submit_button(
            "🛡️ Run compliance check",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not draft.strip():
            st.warning("Please enter marketing content before running a review.")
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

            st.success("Review completed and saved to local review history.")

    result = st.session_state.get("latest_result")

    if result:
        st.divider()
        st.markdown(
            '<div class="section-kicker">03 / Analysis</div>',
            unsafe_allow_html=True,
        )
        st.header("Review overview")

        metric_cols = st.columns(4, gap="medium")
        metric_cols[0].metric("Compliance score", f'{result["score"]}%')
        metric_cols[1].metric("Rules checked", result["total_rules"])
        metric_cols[2].metric("Rule issues", len(result["issues"]))
        metric_cols[3].metric("Risk flags", len(result["detected_risks"]))

        if result["status"] == "PASS":
            st.success(
                "PASS — No configured rule violations or listed risky "
                "phrases were detected."
            )
        else:
            st.warning(
                "NEEDS REVIEW — Inspect the findings and risk flags "
                "before approval."
            )

        st.progress(result["score"] / 100)
        st.caption(
            "The score reflects configured phrase rules only. "
            "Risk flags are separate and do not change the score."
        )

        issue_tab, risk_tab, report_tab = st.tabs([
            "Rule findings",
            "Risky claims",
            "Download report",
        ])

        with issue_tab:
            if result["issues"]:
                for issue in result["issues"]:
                    with st.container(border=True):
                        icon = (
                            "🔴" if issue["Severity"] == "High"
                            else "🟠"
                        )
                        st.markdown(
                            f"### {icon} {issue['Type']} · "
                            f"{issue['Severity']}"
                        )
                        st.write(issue["Finding"])
                        st.markdown("**Suggested correction**")
                        st.write(issue["Suggestion"])
            else:
                st.success("No configured phrase-rule issues found.")

        with risk_tab:
            if result["detected_risks"]:
                st.warning(
                    "These phrases may need evidence and human review. "
                    "Their presence does not prove a claim is false."
                )

                for phrase in result["detected_risks"]:
                    with st.container(border=True):
                        st.markdown(f"**⚠️ {phrase}**")
                        st.write(RISK_GUIDANCE[phrase])
                        st.caption(
                            "Suggested action: check evidence, revise "
                            "wording if needed, and obtain human approval."
                        )
            else:
                st.success(
                    "No phrases from the prototype risk list were detected. "
                    "This does not guarantee factual accuracy or compliance."
                )

        with report_tab:
            st.write(
                "Download a report containing the score, content, "
                "findings, and suggested corrections."
            )
            st.download_button(
                "⬇️ Download review report",
                data=st.session_state["latest_report"] or "",
                file_name="brandguard_review_report.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with st.expander("View original content"):
            st.code(
                st.session_state.get("latest_content", ""),
                language=None,
            )

    st.divider()
    st.markdown(
        '<p class="small-note">BrandGuard AI is a rule-based prototype. '
        'It does not independently verify factual accuracy or guarantee '
        'complete compliance. Human review is required before publication.</p>',
        unsafe_allow_html=True,
    )


# ============================================================
# PAGE 2 — REVIEW HISTORY
# ============================================================
elif page == "Review History":

    st.markdown(
        '<div class="section-kicker">04 / Audit trail</div>',
        unsafe_allow_html=True,
    )
    st.header("Review history")
    st.write(
        "Browse saved reviews in your local SQLite database. "
        "Records remain available while the database file is preserved."
    )

    history = get_review_history()

    if history.empty:
        st.info(
            "No reviews saved yet. Run a content review to create "
            "your first history record."
        )
    else:
        total_reviews = len(history)
        avg_score = round(float(history["Score (%)"].mean()))
        total_issues = int(history["Issues"].sum())

        h1, h2, h3 = st.columns(3)
        h1.metric("Saved reviews", total_reviews)
        h2.metric("Average score", f"{avg_score}%")
        h3.metric("Recorded rule issues", total_issues)

        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Inspect a saved review")

        review_ids = history["Review ID"].tolist()

        selected_id = st.selectbox(
            "Choose a review",
            options=review_ids,
            format_func=lambda review_id: (
                f"Review #{review_id} — "
                + history.loc[
                    history["Review ID"] == review_id,
                    "Reviewed At",
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


# ============================================================
# PAGE 3 — EVIDENCE VERIFICATION
# ============================================================
elif page == "Evidence Verification":

    st.markdown(
        '<div class="section-kicker">05 / Evidence check</div>',
        unsafe_allow_html=True,
    )
    st.header("Evidence-based claim verification")

    st.write(
        "Compare a marketing claim with evidence supplied by the user. "
        "This is a preliminary text comparison, not factual verification."
    )

    claim = st.text_area(
        "Marketing claim",
        placeholder=(
            "Example: Our product improves skin hydration within 24 hours."
        ),
        key="evidence_claim",
    )

    evidence = st.text_area(
        "Supporting evidence",
        placeholder=(
            "Paste a relevant study excerpt, approved document text, "
            "or source notes."
        ),
        key="evidence_text",
    )

    source = st.text_input(
        "Source title or URL (optional)",
        key="evidence_source",
    )

    if st.button(
        "Check claim against evidence",
        type="primary",
        use_container_width=True,
    ):
        if not claim.strip() or not evidence.strip():
            st.warning("Enter both a claim and supporting evidence.")
        else:
            claim_terms = get_terms(claim)
            evidence_terms = get_terms(evidence)

            overlap = claim_terms & evidence_terms

            coverage = (
                len(overlap) / len(claim_terms)
                if claim_terms else 0
            )

            st.subheader("Preliminary result")

            if coverage >= 0.6:
                st.info(
                    "Many claim terms appear in the supplied evidence. "
                    "This does not prove the claim is supported."
                )
            elif coverage > 0:
                st.warning(
                    "Some wording overlaps with the evidence. "
                    "A human reviewer should inspect the source."
                )
            else:
                st.error(
                    "No meaningful wording overlap was found. "
                    "This does not prove the claim is false."
                )

            st.metric("Claim-term overlap", f"{coverage:.0%}")

            st.write(
                "**Overlapping terms:**",
                ", ".join(sorted(overlap)) if overlap else "None",
            )

            if source.strip():
                st.write("**Source provided:**", source)

            st.markdown("### Human review checklist")

            st.checkbox(
                "The source is credible and relevant.",
                key="check_source_credible",
            )
            st.checkbox(
                "The evidence refers to the same product.",
                key="check_same_product",
            )
            st.checkbox(
                "The study date and methodology have been checked.",
                key="check_methodology",
            )
            st.checkbox(
                "The evidence supports the exact wording and timeframe.",
                key="check_exact_claim",
            )

            st.warning(
                "Word overlap is not proof of factual support. Check the "
                "source, study design, product, date, and context before "
                "approving the claim."
            )

            st.caption(
                "This prototype does not retrieve sources, evaluate "
                "scientific quality, or independently establish truth."
            )


# ============================================================
# PAGE 4 — ABOUT BRANDGUARD
# ============================================================
else:

    st.markdown(
        '<div class="section-kicker">06 / Product information</div>',
        unsafe_allow_html=True,
    )
    st.header("About BrandGuard AI")

    st.write(
        "BrandGuard AI is a prototype for reviewing marketing copy "
        "against configurable brand phrase rules."
    )

    st.markdown("### Current capabilities")
    st.markdown("""
    - Prohibited-phrase detection
    - Required-phrase checks
    - Rule-based compliance scoring
    - Suggested corrections for rule violations
    - Risky-claim phrase detection with explanations
    - Preliminary comparison of claim wording with supplied evidence
    - Downloadable review reports
    - Persistent review history using SQLite
    """)

    st.markdown("### Technology")
    st.markdown("""
    - Python and Streamlit for the application interface
    - Regular expressions for phrase matching
    - SQLite for saved review records
    - Pandas for review-history display
    """)

    st.markdown("### Known limitations")
    st.markdown("""
    - The app uses configured phrase rules rather than a trained AI model.
    - Risk flags do not prove that claims are false.
    - Evidence comparison measures word overlap only.
    - The score does not establish factual accuracy or complete compliance.
    - The database is local to this app and is not a shared multi-user database.
    """)


# -------------------------------
# Footer
# -------------------------------
st.divider()
st.caption(
    "🛡️ BrandGuard AI · Midnight Navy + Cyan · "
    "Rule-based prototype"
)
