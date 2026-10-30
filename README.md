# BrandGuard AI

### Marketing Content Screening & Human Review Platform

**BrandGuard AI** is a rule-based prototype that helps teams review marketing content against configurable brand guidelines, identify prohibited phrases, detect missing required terminology, and flag risky claims for human review.

## Live Applications

- **Round 3 Application:** https://brandguard-ai-round3.streamlit.app/
- **Main Application:** https://brandguard-ai.streamlit.app/

## Features

- Configurable brand profiles with required and prohibited phrases.
- High-severity phrase configuration.
- Rule-based content screening and compliance scoring.
- Issue severity levels and suggested corrections.
- Risky-claim phrase detection for human review.
- Persistent review history using SQLite.
- Comparison of earlier and revised content reviews.
- Evidence excerpt comparison using textual overlap.
- Source references and reviewer checklist.
- Downloadable compliance review reports.

## Technology Stack

- Python
- Streamlit
- Pandas
- SQLite
- Regular Expressions (Regex)

## How It Works

1. Select or create a brand profile.
2. Enter marketing content for review.
3. Check the content against configured brand rules.
4. Review the score, triggered findings, severity, and suggestions.
5. Revise the content and compare the new review with an earlier review.
6. Use Evidence Verification to compare a claim with a supplied evidence excerpt.
7. Review saved records and download available reports.

## Technical Approach

BrandGuard AI uses configurable phrase matching and rule-based logic for content screening. SQLite stores brand profiles, review records, and evidence assessments.

The evidence assessment uses textual overlap between a claim and a user-provided excerpt. It supports human review but does not independently establish whether a claim is true or false.

## Limitations

- Does not independently retrieve or authenticate external sources.
- Textual overlap is a heuristic, not semantic or scientific fact verification.
- Risk flags indicate wording that needs attention; they do not prove a claim is false.
- The compliance score reflects configured phrase rules, not legal compliance or factual accuracy.
- Human review is required before final approval.

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/ShaikNajima21/BrandGuardAI.git
cd BrandGuardAI
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it using the appropriate command for your operating system.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
streamlit run app.py
```

## Project Repository

GitHub: https://github.com/ShaikNajima21/BrandGuardAI

## Project Identity

**BrandGuard AI**  
Midnight Navy + Cyan  
Rule-based screening prototype with human review.
