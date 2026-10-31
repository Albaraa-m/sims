from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
DB_PATH = ROOT / "sims.db"
EVIDENCE_DIR = ROOT / "evidence"
LOGS_DIR = ROOT / "logs"

load_dotenv(ROOT / ".env")


def now() -> datetime:
    return datetime.now(UTC)


def evidence_dir(simulation_id: str) -> Path:
    return EVIDENCE_DIR / simulation_id
