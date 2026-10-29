import json
import re
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

# ============================================================
# BrandGuard AI — Round 3
# Brand profiles + claim evidence review + review comparison
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
    :root { --bg:#0b1220; --panel:#111c2e; --line:#293950; --text:#f1f5f9; --muted:#9fb0c5; --cyan:#67e8f9; }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    .stApp { background:radial-gradient(ellipse at 10% 0%,rgba(8,145,178,.15),transparent 35%),linear-gradient(180deg,#0b1220 0%,#0a1020 100%); color:var(--text); }
    [data-testid="stHeader"] { background:rgba(11,18,32,.75); }
    [data-testid="stSidebar"] { background:#0e192a; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] * { color:var(--text); }
    .block-container { max-width:1240px; padding-top:2rem; padding-bottom:3rem; }
    h1,h2,h3 { font-family:'Space Grotesk',sans-serif!important; color:#f8fafc!important; }
    p,label,.stMarkdown { color:var(--text); }
    [data-testid="stMetric"] { background:linear-gradient(145deg,#142238,#101a2b); border:1px solid #2a3b52; padding:18px; border-radius:16px; }
    [data-testid="stMetricLabel"] { color:#9fb0c5!important; }
    [data-testid="stMetricValue"] { color:#67e8f9!important; font-family:'Space Grotesk',sans-serif; }
    .hero { background:linear-gradient(120deg,#111c2e,#122f42); border:1px solid #2b5267; border-radius:22px; padding:28px 30px; margin-bottom:24px; }
    .hero-kicker,.section-kicker { color:#67e8f9; font-size:.76rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase; margin-bottom:8px; }
    .hero-title { font-family:'Space Grotesk',sans-serif; color:#f8fafc; font-size:clamp(2rem,4vw,3rem); font-weight:700; line-height:1.1; margin-bottom:12px; }
    .hero-copy,.muted { color:#b9c9dc; line-height:1.7; }
    .status-pill { display:inline-block; border:1px solid #34546b; background:#102a3a; color:#a5f3fc; border-radius:999px; padding:5px 11px; font-size:.78rem; font-weight:700; }
    div.stButton>button,div.stDownloadButton>button { border-radius:10px; border:1px solid #0891b2; font-weight:700; min-height:2.7rem; }
    div.stButton>button[kind="primary"] { background:linear-gradient(90deg,#0891b2,#06b6d4); color:#061521; border:none; }
    textarea,input,[data-baseweb="select"]>div { background-color:#0e192a!important; border-color:#33465f!important; border-radius:10px!important; }
    [data-testid="stDataFrame"] { border:1px solid #293950; border-radius:12px; overflow:hidden; }
    hr { border-color:#293950; }
    .small-note { color:#8ea2ba; font-size:.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

RISK_GUIDANCE = {
    "best in the world": "Superlative claim: define the comparison and provide reliable evidence.",
    "number one": "Ranking claim: verify the source, category, market, and date.",
    "no. 1": "Ranking claim: verify the source, category, market, and date.",
    "100% effective": "Absolute effectiveness claim: substantiate the exact percentage and context.",
    "100% of customers": "Universal customer-outcome claim: verify the data and methodology.",
    "works for 100% of customers": "Universal customer-outcome claim: verify the data and methodology.",
    "works for everyone": "Absolute claim: check whether reliable evidence supports the statement.",
    "guaranteed results": "Clarify the guarantee terms and verify that the promise can be honored.",
    "guaranteed to work": "Check the conditions and evidence for the promised outcome.",
    "guarantees a complete cure": "Medical outcome claim: requires substantiation and qualified review.",
    "complete cure": "Medical outcome claim: requires substantiation and qualified review.",
    "cure for acne": "Check appropriate medical evidence and applicable advertising rules.",
    "cure all": "Absolute cure claim: requires substantiation and qualified review.",
    "clinically proven": "Identify the clinical study and verify it supports this exact product and claim.",
    "scientifically proven": "Identify credible research supporting the exact statement.",
    "instant results": "Provide evidence for the stated speed and conditions.",
    "in just 24 hours": "Verify evidence supports the stated timeframe.",
    "within 24 hours": "Verify evidence supports the stated timeframe.",
    "results in 24 hours": "Verify evidence supports the stated timeframe.",
    "permanent results": "Provide evidence for the implied duration and conditions.",
    "zero side effects": "Absolute safety claim: qualified review and reliable evidence are needed.",
    "risk-free": "Check whether the wording misleadingly implies no risk.",
    "zero effort": "Check whether the wording creates an unrealistic expectation.",
}


# -------------------------------
# Database and migration functions
# -------------------------------
def db_connection():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    with db_connection() as conn:
        conn.execute("""
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
        existing = {row[1] for row in conn.execute("PRAGMA table_info(reviews)")}
        if "profile_name" not in existing:
            conn.execute("ALTER TABLE reviews ADD COLUMN profile_name TEXT NOT NULL DEFAULT 'Default'")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS brand_profiles (
                name TEXT PRIMARY KEY,
                prohibited_phrases TEXT NOT NULL,
                required_phrases TEXT NOT NULL,
                high_severity_phrases TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS review_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id INTEGER NOT NULL,
                finding_type TEXT NOT NULL,
                phrase TEXT NOT NULL,
                severity TEXT NOT NULL,
                finding TEXT NOT NULL,
                suggestion TEXT NOT NULL,
                FOREIGN KEY(review_id) REFERENCES reviews(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checked_at TEXT NOT NULL,
                claim TEXT NOT NULL,
                evidence TEXT NOT NULL,
                source TEXT,
                overlap_percent INTEGER NOT NULL,
                overlap_terms TEXT NOT NULL,
                assessment TEXT NOT NULL,
                checklist_json TEXT NOT NULL
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM brand_profiles").fetchone()[0]
        if count == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT INTO brand_profiles
                (name, prohibited_phrases, required_phrases, high_severity_phrases, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("Default", "guaranteed, 100% risk-free", "BrandGuard", "guaranteed, 100% risk-free", now, now))


def parse_phrases(text):
    return [phrase.strip() for phrase in text.split(",") if phrase.strip()]


def contains_phrase(text, phrase):
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.IGNORECASE))


def get_profiles():
    with db_connection() as conn:
        rows = conn.execute("""
            SELECT name, prohibited_phrases, required_phrases, high_severity_phrases
            FROM brand_profiles ORDER BY name COLLATE NOCASE
        """).fetchall()
    return {
        row[0]: {
            "prohibited": row[1],
            "required": row[2],
            "high": row[3],
        } for row in rows
    }


def save_profile(name, prohibited, required, high, original_name=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = name.strip()
    if not name:
        raise ValueError("Profile name cannot be empty.")
    if original_name and original_name != name:
        with db_connection() as conn:
            conn.execute("""
                INSERT INTO brand_profiles
                (name, prohibited_phrases, required_phrases, high_severity_phrases, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, prohibited, required, high, now, now))
            conn.execute("DELETE FROM brand_profiles WHERE name = ?", (original_name,))
    else:
        with db_connection() as conn:
            conn.execute("""
                INSERT INTO brand_profiles
                (name, prohibited_phrases, required_phrases, high_severity_phrases, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                  prohibited_phrases=excluded.prohibited_phrases,
                  required_phrases=excluded.required_phrases,
                  high_severity_phrases=excluded.high_severity_phrases,
                  updated_at=excluded.updated_at
            """, (name, prohibited, required, high, now, now))


def delete_profile(name):
    if name == "Default":
        raise ValueError("The Default profile is protected and cannot be deleted.")
    with db_connection() as conn:
        conn.execute("DELETE FROM brand_profiles WHERE name = ?", (name,))


def run_review(content, prohibited_phrases, required_phrases, high_severity_phrases):
    issues = []
    total_rules = 0
    passed_rules = 0
    high_phrases = {p.lower() for p in high_severity_phrases}

    for phrase in prohibited_phrases:
        total_rules += 1
        if contains_phrase(content, phrase):
            severity = "High" if phrase.lower() in high_phrases else "Medium"
            issues.append({
                "Type": "Prohibited phrase", "Phrase": phrase, "Severity": severity,
                "Finding": f"Prohibited phrase detected: '{phrase}'.",
                "Suggestion": f"Remove '{phrase}' or replace it with a specific, supportable statement.",
            })
        else:
            passed_rules += 1

    for phrase in required_phrases:
        total_rules += 1
        if contains_phrase(content, phrase):
            passed_rules += 1
        else:
            issues.append({
                "Type": "Missing required phrase", "Phrase": phrase, "Severity": "Medium",
                "Finding": f"Required phrase is missing: '{phrase}'.",
                "Suggestion": f"Include '{phrase}' naturally if appropriate.",
            })

    score = 100 if total_rules == 0 else round((passed_rules / total_rules) * 100)
    detected_risks = [phrase for phrase in RISK_GUIDANCE if contains_phrase(content, phrase)]
    has_high_issue = any(issue["Severity"] == "High" for issue in issues)
    status = "BLOCK" if has_high_issue else ("NEEDS REVIEW" if issues or detected_risks else "PASS")

    lines = []
    for issue in issues:
        lines.append(f"{issue['Severity']}: {issue['Finding']} Suggestion: {issue['Suggestion']}")
    if not issues:
        lines.append("No configured rule violations detected.")
    if detected_risks:
        lines.append("Risky claims flagged for human review: " + ", ".join(detected_risks))
    findings_text = "\n".join(lines)

    report = "\n".join([
        "BrandGuard AI - Compliance Review Report", "=" * 45,
        f"Review Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Compliance Score: {score}%", f"Rules Checked: {total_rules}",
        f"Issues Found: {len(issues)}", f"Risky Claims Flagged: {len(detected_risks)}",
        f"Status: {status}", "", "Original Marketing Content:", content, "",
        "Findings and Suggestions:", findings_text, "",
        "Note: This rule-based result is a screening aid, not a legal or factual approval.",
    ])
    return {
        "score": score, "total_rules": total_rules, "passed_rules": passed_rules,
        "issues": issues, "detected_risks": detected_risks, "status": status,
        "findings_text": findings_text, "report": report,
    }


def save_review(content, profile_name, result):
    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_connection() as conn:
        cur = conn.execute("""
            INSERT INTO reviews
            (reviewed_at, content, compliance_score, rules_checked, issues_found,
             risky_claims, status, findings, profile_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reviewed_at, content, result["score"], result["total_rules"],
            len(result["issues"]), len(result["detected_risks"]), result["status"],
            result["findings_text"], profile_name
        ))
        review_id = cur.lastrowid
        for issue in result["issues"]:
            conn.execute("""
                INSERT INTO review_findings
                (review_id, finding_type, phrase, severity, finding, suggestion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                review_id, issue["Type"], issue["Phrase"], issue["Severity"],
                issue["Finding"], issue["Suggestion"]
            ))
    return review_id


def get_history():
    with db_connection() as conn:
        return pd.read_sql_query("""
            SELECT id AS 'Review ID', reviewed_at AS 'Reviewed At',
                   profile_name AS 'Brand Profile', compliance_score AS 'Score (%)',
                   rules_checked AS 'Rules Checked', issues_found AS 'Issues',
                   risky_claims AS 'Risky Claims', status AS 'Status'
            FROM reviews ORDER BY id DESC
        """, conn)


def get_review_details(review_id):
    with db_connection() as conn:
        review = conn.execute("""
            SELECT content, findings, profile_name, compliance_score, status, reviewed_at
            FROM reviews WHERE id = ?
        """, (int(review_id),)).fetchone()
        findings = conn.execute("""
            SELECT finding_type, phrase, severity, finding, suggestion
            FROM review_findings WHERE review_id = ? ORDER BY id
        """, (int(review_id),)).fetchall()
    return review, findings


def get_terms(text):
    words = re.findall(r"\b[a-zA-Z0-9'-]+\b", text.lower())
    stop_words = {
        "the", "and", "for", "with", "this", "that", "from", "have", "has", "had",
        "are", "was", "were", "our", "your", "their", "they", "them", "into",
        "after", "before", "within", "which", "will", "would", "could", "should",
        "about", "been", "being", "than", "then", "does", "doesn", "product",
    }
    return {word for word in words if len(word) > 3 and word not in stop_words}



def save_evidence_check(claim, evidence, source, overlap_percent, overlap_terms, assessment, checks):
    with db_connection() as conn:
        conn.execute("""
            INSERT INTO evidence_checks
            (checked_at, claim, evidence, source, overlap_percent, overlap_terms, assessment, checklist_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            claim,
            evidence,
            source,
            overlap_percent,
            ", ".join(sorted(overlap_terms)),
            assessment,
            json.dumps(checks, ensure_ascii=False)
        ))


def get_evidence_history():
    with db_connection() as conn:
        return pd.read_sql_query("""
            SELECT id AS 'ID',
                   checked_at AS 'Saved At',
                   claim AS 'Marketing Claim',
                   source AS 'Source',
                   overlap_percent AS 'Overlap (%)',
                   assessment AS 'Assessment'
            FROM evidence_checks
            ORDER BY id DESC
        """, conn)

initialize_database()

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None
if "latest_report" not in st.session_state:
    st.session_state.latest_report = None
if "latest_content" not in st.session_state:
    st.session_state.latest_content = ""
if "latest_review_id" not in st.session_state:
    st.session_state.latest_review_id = None
if "evidence_assessment" not in st.session_state:
    st.session_state.evidence_assessment = None
if "evidence_assessment_saved" not in st.session_state:
    st.session_state.evidence_assessment_saved = False

profiles = get_profiles()

with st.sidebar:
    st.markdown("## 🛡️ BrandGuard AI")
    st.caption("BRAND INTELLIGENCE")
    st.divider()
    page = st.radio(
        "Workspace",
        ["Content Review", "Brand Profiles", "Review History", "Compare Reviews", "Evidence Verification", "About BrandGuard"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Review engine**")
    st.markdown('<span class="status-pill">Rule-based screening + human review</span>', unsafe_allow_html=True)
    st.write("")
    st.markdown('<p class="muted">Flag configured brand-rule violations and claims that need human attention.</p>', unsafe_allow_html=True)
    st.caption("BrandGuard AI • Round 3 build")

st.markdown("""
<div class="hero">
  <div class="hero-kicker">Brand intelligence platform</div>
  <div class="hero-title">Protect your brand voice.</div>
  <p class="hero-copy">Review marketing content against brand guidelines, flag potentially exaggerated claims, compare claims with supplied evidence, and maintain a traceable review history.</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# PAGE 1 — CONTENT REVIEW
# ============================================================
if page == "Content Review":
    st.markdown('<div class="section-kicker">01 / Brand policy</div>', unsafe_allow_html=True)
    st.header("Configure your guidelines")
    profile_names = list(profiles.keys())
    chosen_profile = st.selectbox("Brand rule profile", profile_names, key="active_profile")
    active = profiles[chosen_profile]
    st.caption("To create or edit saved profiles, open **Brand Profiles** in the sidebar.")

    left, right = st.columns(2, gap="large")
    with left:
        prohibited_input = st.text_area(
            "Prohibited words or phrases", value=active["prohibited"],
            help="Comma-separated. Changes here apply to this review; use Brand Profiles to save changes.",
            height=105, key=f"prohibited_{chosen_profile}",
        )
    with right:
        required_input = st.text_area(
            "Required words or phrases", value=active["required"],
            help="Comma-separated. Add only phrases that genuinely fit your brand policy.",
            height=105, key=f"required_{chosen_profile}",
        )
    high_input = st.text_input(
        "High-severity prohibited phrases", value=active["high"],
        help="Comma-separated. These configured violations cause BLOCK status.",
        key=f"high_{chosen_profile}",
    )

    st.divider()
    st.markdown('<div class="section-kicker">02 / Content workspace</div>', unsafe_allow_html=True)
    st.header("Review marketing content")
    st.write("Run configured phrase checks and identify selected claims that need human review.")
    with st.form("brandguard_review_form", clear_on_submit=False):
        draft = st.text_area("Marketing draft", height=220, placeholder="Example: BrandGuard helps teams review marketing content...")
        submitted = st.form_submit_button("🛡️ Run compliance check", type="primary", use_container_width=True)

    if submitted:
        if not draft.strip():
            st.warning("Please enter marketing content before running a review.")
        else:
            result = run_review(
                draft, parse_phrases(prohibited_input), parse_phrases(required_input),
                parse_phrases(high_input),
            )
            review_id = save_review(draft, chosen_profile, result)
            st.session_state.latest_result = result
            st.session_state.latest_report = result["report"]
            st.session_state.latest_content = draft
            st.session_state.latest_review_id = review_id
            st.success(f"Review #{review_id} completed and saved to local history.")

    result = st.session_state.latest_result
    if result:
        st.divider()
        st.markdown('<div class="section-kicker">03 / Analysis</div>', unsafe_allow_html=True)
        st.header("Review overview")
        cols = st.columns(4, gap="medium")
        cols[0].metric("Compliance score", f'{result["score"]}%')
        cols[1].metric("Rules checked", result["total_rules"])
        cols[2].metric("Rule issues", len(result["issues"]))
        cols[3].metric("Risk flags", len(result["detected_risks"]))

        if result["status"] == "PASS":
            st.success("PASS — No configured rule violations or listed risky phrases were detected.")
        elif result["status"] == "BLOCK":
            st.error("BLOCK — At least one high-severity configured rule was triggered. Do not approve without resolution.")
        else:
            st.warning("NEEDS REVIEW — Inspect findings and risk flags before approval.")
        st.progress(result["score"] / 100)
        st.caption("The score reflects configured phrase rules only. Risk flags are separate and do not change the score.")

        issue_tab, risk_tab, report_tab = st.tabs(["Rule findings", "Risky claims", "Download report"])
        with issue_tab:
            if result["issues"]:
                for issue in result["issues"]:
                    with st.container(border=True):
                        icon = "🔴" if issue["Severity"] == "High" else "🟠"
                        st.markdown(f"### {icon} {issue['Type']} · {issue['Severity']}")
                        st.write(issue["Finding"])
                        st.markdown("**Suggested correction**")
                        st.write(issue["Suggestion"])
            else:
                st.success("No configured phrase-rule issues found.")
        with risk_tab:
            if result["detected_risks"]:
                st.warning("These phrases may need evidence and human review. Their presence does not prove a claim is false.")
                for phrase in result["detected_risks"]:
                    with st.container(border=True):
                        st.markdown(f"**⚠️ {phrase}**")
                        st.write(RISK_GUIDANCE[phrase])
                        st.caption("Suggested action: check evidence, revise wording if needed, and obtain human approval.")
            else:
                st.success("No phrases from the prototype risk list were detected. This does not guarantee factual accuracy or compliance.")
        with report_tab:
            st.download_button("⬇️ Download review report", data=st.session_state.latest_report or "",
                               file_name=f"brandguard_review_{st.session_state.latest_review_id}.txt",
                               mime="text/plain", use_container_width=True)
        with st.expander("View original content"):
            st.code(st.session_state.latest_content, language=None)

    st.divider()
    st.markdown('<p class="small-note">BrandGuard AI is a screening prototype. It does not independently verify factual accuracy or guarantee legal compliance.</p>', unsafe_allow_html=True)

# ============================================================
# PAGE 2 — BRAND PROFILES
# ============================================================
elif page == "Brand Profiles":
    st.markdown('<div class="section-kicker">02 / Reusable policies</div>', unsafe_allow_html=True)
    st.header("Brand profile manager")
    st.write("Create and save different phrase policies for different brands or campaigns. Profiles are stored in your local SQLite database.")
    profile_names = list(profiles.keys())
    mode = st.radio("Action", ["Edit existing profile", "Create new profile"], horizontal=True)
    original = st.selectbox("Choose profile to edit", profile_names) if mode == "Edit existing profile" else None
    data = profiles[original] if original else {"prohibited": "", "required": "", "high": ""}
    default_name = original if original else ""
    with st.form("profile_editor"):
        profile_name = st.text_input("Profile name", value=default_name, max_chars=80)
        profile_prohibited = st.text_area("Prohibited phrases (comma-separated)", value=data["prohibited"], height=100)
        profile_required = st.text_area("Required phrases (comma-separated)", value=data["required"], height=100)
        profile_high = st.text_area("High-severity phrases (comma-separated)", value=data["high"], height=90,
                                    help="Must also be listed among prohibited phrases to trigger BLOCK status.")
        save_clicked = st.form_submit_button("Save brand profile", type="primary", use_container_width=True)
    if save_clicked:
        if not profile_name.strip():
            st.error("Enter a profile name.")
        elif mode == "Create new profile" and profile_name.strip() in profiles:
            st.error("A profile with that name already exists. Choose another name.")
        elif mode == "Edit existing profile" and profile_name.strip() != original and profile_name.strip() in profiles:
            st.error("That profile name is already in use.")
        else:
            try:
                save_profile(profile_name, profile_prohibited, profile_required, profile_high, original_name=original)
                st.success(f"Profile '{profile_name.strip()}' saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save profile: {exc}")
    st.divider()
    st.subheader("Saved profiles")
    st.dataframe(pd.DataFrame([
        {"Profile": name, "Prohibited phrases": item["prohibited"], "Required phrases": item["required"],
         "High-severity phrases": item["high"]}
        for name, item in profiles.items()
    ]), use_container_width=True, hide_index=True)
    if original and original != "Default":
        if st.button(f"Delete profile '{original}'", type="secondary"):
            try:
                delete_profile(original)
                st.success("Profile deleted. Historical reviews are preserved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    st.caption("Editing a profile affects future reviews; historical review records remain unchanged.")

# ============================================================
# PAGE 3 — REVIEW HISTORY
# ============================================================
elif page == "Review History":
    st.markdown('<div class="section-kicker">03 / Audit trail</div>', unsafe_allow_html=True)
    st.header("Review history")
    st.write("Browse saved reviews in your local SQLite database. Keep the database file to preserve records.")
    history = get_history()
    if history.empty:
        st.info("No reviews saved yet. Run a content review to create your first record.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Saved reviews", len(history))
        c2.metric("Average score", f'{round(float(history["Score (%)"].mean()))}%')
        c3.metric("Recorded rule issues", int(history["Issues"].sum()))
        st.dataframe(history, use_container_width=True, hide_index=True)
        st.markdown("### Inspect a saved review")
        review_ids = history["Review ID"].tolist()
        selected_id = st.selectbox("Choose a review", review_ids,
            format_func=lambda rid: f"Review #{rid} — " + history.loc[history["Review ID"] == rid, "Reviewed At"].iloc[0])
        details, findings = get_review_details(selected_id)
        if details:
            with st.container(border=True):
                st.caption(f"Profile: {details[2]} · Score: {details[3]}% · Status: {details[4]} · {details[5]}")
                st.markdown("**Original marketing content**")
                st.code(details[0], language=None)
                st.markdown("**Review findings**")
                st.text(details[1])
                if findings:
                    st.markdown("**Finding details**")
                    st.dataframe(pd.DataFrame(findings, columns=["Type", "Phrase", "Severity", "Finding", "Suggestion"]),
                                 use_container_width=True, hide_index=True)

# ============================================================
# PAGE 4 — COMPARE REVIEWS
# ============================================================
elif page == "Compare Reviews":
    st.markdown('<div class="section-kicker">04 / Revision tracking</div>', unsafe_allow_html=True)
    st.header("Compare two saved reviews")
    st.write("Compare an earlier draft with a revised draft. Findings are matched by type and phrase; this is a rule-based comparison.")
    history = get_history()
    if len(history) < 2:
        st.info("Save at least two content reviews to compare drafts.")
    else:
        ids = history["Review ID"].tolist()
        def label_for(rid):
            row = history.loc[history["Review ID"] == rid].iloc[0]
            return f"Review #{rid} · {row['Reviewed At']} · {row['Score (%)']}% · {row['Status']}"
        older_id = st.selectbox("Earlier review", ids, index=min(1, len(ids)-1), format_func=label_for, key="compare_older")
        newer_options = [rid for rid in ids if rid != older_id]
        newer_id = st.selectbox("Revised review", newer_options, format_func=label_for, key="compare_newer")
        older, older_findings = get_review_details(older_id)
        newer, newer_findings = get_review_details(newer_id)
        if older and newer:
            col1, col2, col3 = st.columns(3)
            col1.metric("Earlier score", f"{older[3]}%")
            col2.metric("Revised score", f"{newer[3]}%")
            col3.metric("Score change", f"{newer[3] - older[3]:+d} points")
            st.markdown("### Drafts")
            a, b = st.columns(2)
            with a:
                st.markdown(f"**Earlier · Review #{older_id}**")
                st.code(older[0], language=None)
            with b:
                st.markdown(f"**Revised · Review #{newer_id}**")
                st.code(newer[0], language=None)
            old_set = {(f[0], f[1]) for f in older_findings}
            new_set = {(f[0], f[1]) for f in newer_findings}
            resolved = sorted(old_set - new_set)
            remaining = sorted(old_set & new_set)
            added = sorted(new_set - old_set)
            r1, r2, r3 = st.columns(3)
            r1.metric("Earlier findings resolved", len(resolved))
            r2.metric("Findings still present", len(remaining))
            r3.metric("New findings", len(added))
            def show_pairs(title, pairs, empty_text):
                st.markdown(f"### {title}")
                if pairs:
                    st.dataframe(pd.DataFrame(pairs, columns=["Finding type", "Phrase"]), use_container_width=True, hide_index=True)
                else:
                    st.success(empty_text)
            show_pairs("Resolved since earlier review", resolved, "No earlier findings were resolved, or the earlier review had none.")
            show_pairs("Still present", remaining, "No matching earlier findings remain.")
            show_pairs("New in revised review", added, "No new rule findings detected.")
            st.caption("A finding counts as resolved when the same finding type + phrase is absent in the newer saved review. This does not replace human approval.")

# ============================================================
# PAGE 5 — EVIDENCE VERIFICATION
# ============================================================
elif page == "Evidence Verification":
    st.markdown('<div class="section-kicker">05 / Source-grounded review</div>', unsafe_allow_html=True)
    st.header("Claim evidence review")
    st.write("Paste the exact claim, relevant evidence excerpt, and source reference. The app checks wording overlap and records a reviewer checklist; it does not independently prove truth.")
    claim = st.text_area("Marketing claim", placeholder="Example: Our product improves skin hydration within 24 hours.", key="evidence_claim")
    evidence = st.text_area("Evidence excerpt", placeholder="Paste a relevant study excerpt or approved source text.", key="evidence_text")
    source = st.text_input("Source title, URL, document ID, or citation", key="evidence_source")
    st.caption("Use a source that you have permission to use. A URL or title alone is not evidence; paste the relevant excerpt too.")
    st.markdown("### Human verification checklist")
    c1 = st.checkbox("I checked that the source is authentic and credible.", key="ev_credible")
    c2 = st.checkbox("The evidence refers to the same product, population, and use case.", key="ev_product")
    c3 = st.checkbox("I checked the study date, methodology, and limitations.", key="ev_method")
    c4 = st.checkbox("The evidence supports the exact claim, including numbers and timeframe.", key="ev_exact")
    c5 = st.checkbox("A qualified reviewer has reviewed the claim where required.", key="ev_reviewer")
    if st.button("Assess supplied evidence", type="primary", use_container_width=True):
        if not claim.strip() or not evidence.strip():
            st.warning("Enter both the claim and the evidence excerpt.")
        else:
            claim_terms = get_terms(claim)
            evidence_terms = get_terms(evidence)
            overlap = claim_terms & evidence_terms
            coverage = len(overlap) / len(claim_terms) if claim_terms else 0
            checks = {
                "Source authentic and credible": c1,
                "Same product/population/use case": c2,
                "Date/methodology/limitations checked": c3,
                "Exact claim supported": c4,
                "Qualified reviewer checked": c5,
            }
            if not overlap:
                assessment = "INSUFFICIENT TEXTUAL OVERLAP — HUMAN REVIEW REQUIRED"
            elif all(checks.values()):
                assessment = "CHECKLIST COMPLETE — READY FOR FINAL HUMAN DECISION"
            else:
                assessment = "NEEDS HUMAN REVIEW"
            st.session_state.evidence_assessment = {
                "claim": claim, "evidence": evidence, "source": source.strip(),
                "coverage": coverage, "overlap": sorted(overlap),
                "assessment": assessment, "checks": checks,
            }
            st.session_state.evidence_assessment_saved = False

    assessment_data = st.session_state.evidence_assessment
    if assessment_data:
        st.subheader("Assessment")
        st.metric("Claim-term overlap", f"{assessment_data['coverage']:.0%}")
        st.write("**Assessment:**", assessment_data["assessment"])
        st.write("**Overlapping terms:**", ", ".join(assessment_data["overlap"]) if assessment_data["overlap"] else "None")
        st.write("**Source supplied:**", assessment_data["source"] or "No source reference provided")
        st.markdown("**Checklist status**")
        for label, checked in assessment_data["checks"].items():
            st.write(f"{'✅' if checked else '⬜'} {label}")
        if "INSUFFICIENT" in assessment_data["assessment"]:
            st.warning("The claim and evidence share no meaningful terms. This does not prove the claim is false.")
        elif "CHECKLIST COMPLETE" in assessment_data["assessment"]:
            st.success("All reviewer checklist items are checked. This records the reviewer's checks; the app itself has not verified the truth of the claim.")
        else:
            st.info("Some claim wording overlaps with the evidence, but the checklist is incomplete. Do not treat overlap as proof.")
        if not st.session_state.evidence_assessment_saved:
            if st.button("Save evidence assessment", type="secondary"):
                save_evidence_check(
                    assessment_data["claim"], assessment_data["evidence"],
                    assessment_data["source"], round(assessment_data["coverage"] * 100),
                    set(assessment_data["overlap"]), assessment_data["assessment"],
                    assessment_data["checks"],
                )
                st.session_state.evidence_assessment_saved = True
                st.success("Evidence assessment saved.")
        else:
            st.success("Evidence assessment saved.")
        st.warning("This is not automated fact-checking. Verify the cited source and the full context before approving publication.")

    st.divider()
    st.subheader("Saved evidence assessments")

    evidence_history = get_evidence_history()

    if evidence_history.empty:
        st.info("No evidence assessments saved yet.")
    else:
        st.dataframe(
            evidence_history,
            use_container_width=True,
            hide_index=True
        )

# ============================================================
# PAGE 6 — ABOUT
# ============================================================
else:
    st.markdown('<div class="section-kicker">06 / Product information</div>', unsafe_allow_html=True)
    st.header("About BrandGuard AI")
    st.write("BrandGuard AI is a prototype for screening marketing copy against configurable brand phrase rules and organizing human review.")
    st.markdown("### Current capabilities")
    st.markdown("""
    - Saved brand profiles with required and prohibited phrases
    - Configurable high-severity rules with BLOCK / NEEDS REVIEW / PASS outcomes
    - Phrase-rule scoring and suggested corrections
    - Risky-claim phrase flags with explanations
    - Evidence excerpt comparison, source reference, and reviewer checklist
    - Persistent review records and finding details in SQLite
    - Comparison of earlier and revised reviews
    - Downloadable content review reports
    """)
    st.markdown("### Technology")
    st.markdown("- Python and Streamlit\n- Regular expressions for phrase matching\n- SQLite for saved profiles, reviews, and evidence assessments\n- Pandas for review-history tables")
    st.markdown("### Known limitations")
    st.markdown("""
    - The app does not independently retrieve or authenticate sources.
    - Evidence overlap is a text heuristic, not semantic or scientific verification.
    - The reviewer checklist records user assertions; it does not validate them.
    - Risk flags do not prove a claim is false.
    - Scores reflect configured phrase rules only and are not legal-compliance scores.
    - The database is local to this app and is not a shared multi-user database.
    """)

st.divider()
st.caption("🛡️ BrandGuard AI · Midnight Navy + Cyan · Rule-based screening prototype")
