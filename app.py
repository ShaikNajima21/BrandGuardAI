
import re
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

# -------------------------------
# Page configuration
# -------------------------------
st.set_page_config(
    page_title="BrandGuard AI",
    page_icon="🛡️",
    layout="wide"
)

DB_NAME = "brandguard_history.db"


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


initialize_database()


# -------------------------------
# Helper functions
# -------------------------------
def contains_phrase(text, phrase):
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return bool(re.search(pattern, text, re.IGNORECASE))


def parse_phrases(text):
    return [phrase.strip() for phrase in text.split(",") if phrase.strip()]


# -------------------------------
# Application heading
# -------------------------------
st.title("🛡️ BrandGuard AI")
st.caption("Brand compliance and content risk review")

st.write(
    "Review marketing content against configured brand guidelines, "
    "identify potentially exaggerated claims, and view previous reviews."
)

st.info(
    "This prototype uses rule-based checks. Its score reflects only "
    "the configured required and prohibited phrase rules; it does not "
    "prove that content is factually correct or fully brand-compliant."
)

st.divider()


# -------------------------------
# 1. Brand guidelines
# -------------------------------
st.header("1. Brand Guidelines")

col1, col2 = st.columns(2)

with col1:
    prohibited_input = st.text_area(
        "Prohibited words or phrases (comma-separated)",
        value="guaranteed, 100% risk-free",
        help="Content containing any of these phrases will be flagged."
    )

with col2:
    required_input = st.text_area(
        "Required words or phrases (comma-separated)",
        value="BrandGuard",
        help="Content must contain each configured required phrase."
    )


# -------------------------------
# 2. Content review
# -------------------------------
st.header("2. Content Review")

draft = st.text_area(
    "Enter your marketing content",
    height=180,
    placeholder="Paste your marketing content here..."
)

check_button = st.button("Check Content", type="primary")


if check_button:
    if not draft.strip():
        st.warning("Please enter some marketing content first.")

    else:
        issues = []
        total_rules = 0
        passed_rules = 0

        prohibited_phrases = parse_phrases(prohibited_input)
        required_phrases = parse_phrases(required_input)

        # Check prohibited phrases
        for phrase in prohibited_phrases:
            total_rules += 1

            if contains_phrase(draft, phrase):
                issues.append({
                    "Type": "Prohibited phrase",
                    "Phrase": phrase,
                    "Severity": "High",
                    "Finding": f"Prohibited phrase detected: '{phrase}'.",
                    "Suggestion": (
                        f"Remove '{phrase}' or replace it with a "
                        "specific, supportable statement."
                    )
                })
            else:
                passed_rules += 1

        # Check required phrases
        for phrase in required_phrases:
            total_rules += 1

            if contains_phrase(draft, phrase):
                passed_rules += 1
            else:
                issues.append({
                    "Type": "Missing required phrase",
                    "Phrase": phrase,
                    "Severity": "Medium",
                    "Finding": f"Required phrase is missing: '{phrase}'.",
                    "Suggestion": (
                        f"Include '{phrase}' naturally if appropriate "
                        "for the content."
                    )
                })

        # Calculate compliance score
        if total_rules == 0:
            score = 100
        else:
            score = round((passed_rules / total_rules) * 100)

        # Identify risky claims for human review
        risky_phrases = [
            "best in the world",
            "number one",
            "no. 1",
            "100% effective",
            "instant results",
            "cure all",
            "zero effort"
        ]

        detected_risks = [
            phrase for phrase in risky_phrases
            if contains_phrase(draft, phrase)
        ]

        # Risky claims require review but do not change the score
        status = "NEEDS REVIEW" if issues or detected_risks else "PASS"

        # Prepare findings for history and report
        finding_lines = []

        if issues:
            for issue in issues:
                finding_lines.append(
                    f"{issue['Severity']}: {issue['Finding']} "
                    f"Suggestion: {issue['Suggestion']}"
                )
        else:
            finding_lines.append("No configured rule violations detected.")

        if detected_risks:
            finding_lines.append(
                "Risky claims flagged for human review: "
                + ", ".join(detected_risks)
            )

        findings_text = "\n".join(finding_lines)

        # Save this review to SQLite
        save_review(
            content=draft,
            score=score,
            rules_checked=total_rules,
            issues_found=len(issues),
            risky_claims=len(detected_risks),
            status=status,
            findings=findings_text
        )

        # Store report for download
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
            draft,
            "",
            "Findings and Suggestions:",
            findings_text,
            "",
            "Note: This is a rule-based prototype. Human review is "
            "required for context, factual accuracy, and final approval."
        ]

        st.session_state["latest_report"] = "\n".join(report_lines)

        # -------------------------------
        # 3. Review results
        # -------------------------------
        st.divider()
        st.header("3. Review Results")

        metric1, metric2, metric3 = st.columns(3)

        metric1.metric("Compliance Score", f"{score}%")
        metric2.metric("Configured Rules", total_rules)
        metric3.metric("Rule Issues", len(issues))

        if status == "PASS":
            st.success("No configured issues or flagged risky claims detected.")
        else:
            st.warning(
                "This content needs review before approval. "
                "Check the findings below."
            )

        if issues:
            st.subheader("Detected Rule Issues")

            for issue in issues:
                with st.container(border=True):
                    st.markdown(
                        f"**{issue['Type']} — {issue['Severity']} severity**"
                    )
                    st.write(issue["Finding"])
                    st.write(f"**Suggested correction:** {issue['Suggestion']}")

        else:
            st.success("No configured prohibited or missing-phrase issues found.")

        # -------------------------------
        # 4. Risky claim review
        # -------------------------------
        st.header("4. Risky Claim Review")

        if detected_risks:
            st.warning(
                "The following phrases may need evidence or human review. "
                "They are not automatically treated as false."
            )

            for phrase in detected_risks:
                st.write(f"- **{phrase}**")
        else:
            st.write("No phrases from the prototype's risky-claim list were detected.")

        st.caption(
            "Risky-claim flags are separate from the compliance score."
        )

        # -------------------------------
        # Download report
        # -------------------------------
        st.download_button(
            label="Download Review Report",
            data=st.session_state["latest_report"],
            file_name="brandguard_review_report.txt",
            mime="text/plain"
        )


# -------------------------------
# 5. Review history
# -------------------------------
st.divider()
st.header("5. Review History")

st.write(
    "Previous reviews are stored locally in SQLite and remain available "
    "after restarting the app, as long as the database file is preserved."
)

history = get_review_history()

if history.empty:
    st.info(
        "No reviews saved yet. Enter content above and click "
        "'Check Content' to create your first history record."
    )

else:
    st.dataframe(
        history,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("View a saved review")

    review_ids = history["Review ID"].tolist()

    selected_id = st.selectbox(
        "Choose a review",
        options=review_ids,
        format_func=lambda review_id: (
            f"Review #{review_id} — "
            + history.loc[
                history["Review ID"] == review_id,
                "Reviewed At"
            ].iloc[0]
        )
    )

    details = get_review_details(selected_id)

    if details:
        st.markdown("**Original marketing content**")
        st.code(details[0], language=None)

        st.markdown("**Review findings**")
        st.text(details[1])


# -------------------------------
# Footer
# -------------------------------
st.divider()

st.caption(
    "BrandGuard AI | Rule-based brand compliance review prototype"
)
