
# BrandGuard AI

### Brand Intelligence Platform

BrandGuard AI is a rule-based prototype that helps teams review marketing content against configured brand guidelines, identify prohibited phrases, detect missing required terminology, and flag risky claims for human review.

## Features

- Rule-based brand compliance checks
- Configurable prohibited and required phrases
- Compliance score based on configured phrase rules
- Issue severity levels and suggested corrections
- Risky claim detection for human review
- Downloadable compliance review reports
- SQLite-based review history
- Review findings and status tracking

## Technology Stack

- Python
- Streamlit
- Pandas
- SQLite
- Regular expressions (Regex)

## How It Works

1. Enter marketing content.
2. Check it against the configured phrase rules.
3. Review the compliance score, detected issues, and suggestions.
4. Examine risky claims that require human judgment.
5. Download the report and review saved history.

## Limitations

BrandGuard AI is a rule-based prototype. It does not independently verify factual claims or guarantee complete brand compliance. Human review is required before final approval.

## Run Locally

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
python -m streamlit run app.py
```
