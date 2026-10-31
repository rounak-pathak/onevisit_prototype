# ONEVISIT — Citizen Application Readiness Checker

**Team:** Sloths  
**Primary MYBharat theme:** Governance & Civic Technology  
**Prototype status:** Working local MVP; illustrative rules only.

ONEVISIT helps a citizen check an application document set *before* visiting a service counter. Select a service, upload text-based PDF/TXT/CSV/MD documents, and receive a readiness report that flags missing document categories, explicit expired dates and possible name variations across files.

It is designed to reduce avoidable repeat visits and make service requirements easier to prepare for. It does **not** approve applications, determine legal eligibility or replace an official checklist.

## Features in this prototype

- Four demo service profiles: Scholarship, Pension, Ration card and College admission.
- Text extraction from text-based PDFs using `pypdf`; UTF-8 text files are supported.
- Heuristic document classification by filename and visible text.
- Missing-document-category checks against service-specific example checklists.
- Expiry-date alerts when a document explicitly states a validity date.
- Cross-document name variation checks using string similarity.
- Severity-labelled issues, a simple explainable readiness score and suggested next steps.
- Downloadable JSON audit report.
- Synthetic sample data; uploaded files are processed in memory and are not intentionally persisted.

## Requirements

- Python 3.10 or newer.
- `pypdf` dependency (installed from `requirements.txt`).
- No API key, database, cloud account or custom hardware is required.

## Run locally

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Windows

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py app.py
```

Open **http://127.0.0.1:5055** and select **Run sample demo**.

## Configuration

| Environment variable | Default | Purpose |
|---|---:|---|
| `ONEVISIT_HOST` | `127.0.0.1` | Bind address. Keep localhost for private testing. |
| `ONEVISIT_PORT` | `5055` | Local HTTP port. |
| `ONEVISIT_MAX_UPLOAD_MB` | `15` | Maximum request size in MB. |

No secrets or external API credentials are used by this MVP.

## Project structure

```text
onevisit_prototype/
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
├── run_mac_linux.sh
├── run_windows.bat
├── sample_documents/
│   ├── 01_identity_proof.txt
│   ├── 02_income_certificate.txt
│   ├── 03_bank_passbook.txt
│   └── 04_student_certificate.txt
├── tests/
│   └── test_engine.py
└── docs/
    ├── TECHNICAL_DESIGN.md
    ├── REQUIREMENTS_MAPPING.md
    └── PRIVACY_AND_RISK.md
```

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover the bundled synthetic scenario, expiry detection, name-variation detection, missing-document detection and service-specific required categories.

## Important limitations

1. Built-in document checklists are **fictional demonstration rules**, not official MYBharat, state or department requirements.
2. Extraction is not OCR. Scanned/image-only PDFs may produce no text; use readable, text-based PDFs or TXT files.
3. Name similarity and date extraction are heuristics. A warning can be a false positive or miss a real issue.
4. The score is a transparent prototype heuristic, **not** a probability of approval.
5. The app has no authentication, authorization, encryption-at-rest, formal audit log or production security review. Do not upload actual Aadhaar, bank, income or other sensitive documents to an internet-facing deployment.
6. Production use requires verified, versioned, state-specific checklists with official source URLs and effective dates, user consent, secure storage/deletion controls, accessibility and language testing, and human review.

## Roadmap

- Verified state/department rule packs with source citations and effective dates.
- Regional-language and voice guidance.
- OCR with confidence scoring and manual correction.
- User-controlled redaction and secure account/storage layer.
- Accessibility and assisted-service-centre workflows.
- Pilot evaluation measuring avoidable repeat visits, preparation time, false-positive rate and user comprehension.

## Open-source licence

MIT. See `LICENSE`.
