from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "sims.db"
EVIDENCE_DIR = ROOT / "evidence"
LOGS_DIR = ROOT / "logs"

load_dotenv(ROOT / ".env")


def now() -> datetime:
    return datetime.now(UTC)


LLM_MODEL = "google/gemma-4-31b-it"
