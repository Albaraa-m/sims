import asyncio

import pytest

from simulations import evidence


@pytest.fixture(autouse=True)
def evidence_in_tmp_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "EVIDENCE_DIR", tmp_path)


def test_written_evidence_is_read_back(tmp_path):
    recording = tmp_path / "session.ogg"
    recording.write_bytes(b"audio")

    evidence.write_evidence("sim1", {"chat_history": {}}, recording)
    collected = asyncio.run(evidence.wait_for_evidence("sim1", timeout=1))

    assert collected["report"] == {"chat_history": {}}
    assert collected["recording_path"] is not None


def test_missing_report_times_out():
    with pytest.raises(TimeoutError):
        asyncio.run(evidence.wait_for_evidence("missing", timeout=0))
