import asyncio
import json
import shutil
import time
from pathlib import Path

from core.config import EVIDENCE_DIR

REPORT_FILE = "report.json"
RECORDING_FILE = "audio.ogg"


def evidence_dir(simulation_id: str) -> Path:
    return EVIDENCE_DIR / simulation_id


def write_evidence(simulation_id: str, report: dict, recording: Path | None) -> None:
    directory = evidence_dir(simulation_id)
    directory.mkdir(parents=True, exist_ok=True)
    if recording and recording.exists():
        shutil.copy(recording, directory / RECORDING_FILE)
    # Written last: the report is the signal that evidence is complete.
    (directory / REPORT_FILE).write_text(json.dumps(report))


async def wait_for_evidence(simulation_id: str, timeout: float) -> dict:
    directory = evidence_dir(simulation_id)
    report_file = directory / REPORT_FILE
    deadline = time.monotonic() + timeout
    while not report_file.exists():
        if time.monotonic() > deadline:
            raise TimeoutError(
                "call ended but the booking agent saved no session report"
            )
        await asyncio.sleep(1)

    recording = directory / RECORDING_FILE
    return {
        "report": json.loads(report_file.read_text()),
        "recording_path": str(recording) if recording.exists() else None,
    }
