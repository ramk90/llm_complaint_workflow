# AI Customer Complaint Workflow

This project processes customer complaint documents using a Python workflow powered by Google Gemini. It ingests complaint files, extracts structured facts, generates a customer-facing response email, produces an internal executive summary, and saves all outputs into organized folders.

## What this project does

- Reads complaint documents from `.txt`, `.pdf`, and `.docx` files
- Extracts structured complaint metadata with LLM-based analysis
- Identifies category, urgency, sentiment, risk, and root cause
- Drafts a customer response email tailored to the complaint
- Generates an internal executive summary for operations teams
- Writes JSON, email text, summary text, and a consolidated CSV report
- Supports single-file and batch processing modes

## Project structure

```text
.
├── app.py                     # FastAPI service
├── main.py                    # CLI entry point
├── Dockerfile                 # Container build file
├── requirements.txt           # Python dependencies
├── data/                      # Sample complaint files
├── output/                    # Generated workflow results
│   ├── final_report.csv
│   ├── structured_data/
│   ├── customer_emails/
│   └── case_summaries/
├── src/
│   ├── __init__.py
│   ├── chains.py              # LLM prompt orchestration
│   ├── config.py             # Config and directory setup
│   ├── ingest.py             # File parsing / text extraction
│   ├── orchestrator.py       # Workflow orchestration
│   └── schemas.py            # Pydantic models and result objects
├── tests/                    # Regression tests
├── .env                      # Local environment variables
├── .env.local                # Optional local overrides
└── .gitignore
```

## Requirements

- Python 3.10+
- Google Gemini API access
- Required Python packages listed in `requirements.txt`

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your configuration:

```env
GEMINI_API_KEY=your_api_key_here
DEFAULT_MODEL=gemini-3.6-flash
DATA_DIR=./data
OUTPUT_DIR=./output
MAX_WORKERS=4
```

> The project loads environment variables from `.env` automatically through `python-dotenv`.

## Run the CLI

### Single file mode

```bash
python main.py --file data/complaint_01_billing.txt
```

### Batch mode

```bash
python main.py --data-dir data --output-dir output --workers 4
```

### Verbose logging

```bash
python main.py --verbose
```

## Run the API service

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Available FastAPI endpoints include:

- `GET /` - service overview
- `GET /health` - health check
- `POST /trigger` - batch processing trigger
- `POST /process-file` - upload a single file for processing

## Outputs generated

After processing, the project creates these outputs under the configured output directory:

- `final_report.csv` - consolidated case report
- `structured_data/` - per-file JSON structured analysis
- `customer_emails/` - generated customer email drafts
- `case_summaries/` - executive summaries for operations teams

## Example of a processing flow

1. Load complaint file text
2. Detect file type and extract text
3. Send content to Gemini with a structured schema
4. Parse a validated `ComplaintAnalysis`
5. Generate a response email
6. Generate an internal executive summary
7. Save outputs and write CSV report

## Notes

- Batch processing uses a thread pool and preserves deterministic ordering when writing the final CSV report.
- If a requested output directory does not exist, the project creates it automatically.
- Unsupported file types raise a clear validation error.
