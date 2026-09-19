import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output"))

# Output subdirectories
STRUCTURED_DATA_DIR = OUTPUT_DIR / "structured_data"
CUSTOMER_EMAILS_DIR = OUTPUT_DIR / "customer_emails"
CASE_SUMMARIES_DIR = OUTPUT_DIR / "case_summaries"
FINAL_REPORT_PATH = OUTPUT_DIR / "final_report.csv"

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-3.6-flash")
GENAI_TIMEOUT_MS = int(os.getenv("GENAI_TIMEOUT_MS", "60000"))

# Concurrency
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
MAX_LLM_CONCURRENCY = int(os.getenv("MAX_LLM_CONCURRENCY", "2"))


def ensure_directories(base_dir: Path | str | None = None):
    """Ensure all required input/output directories exist for a given base path."""
    output_root = Path(base_dir) if base_dir is not None else OUTPUT_DIR
    structured_dir = output_root / "structured_data"
    customer_dir = output_root / "customer_emails"
    case_dir = output_root / "case_summaries"

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    structured_dir.mkdir(parents=True, exist_ok=True)
    customer_dir.mkdir(parents=True, exist_ok=True)
    case_dir.mkdir(parents=True, exist_ok=True)


# Auto-create output directories on import
ensure_directories()
