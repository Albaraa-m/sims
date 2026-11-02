import os

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.routes.system import is_sims_worker_process
from simulations.queue import RunRequest, admit_runs
from simulations.worker_registry import register_worker


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_queue_state_counts_runs_and_lists_live_workers(client):
    admit_runs([RunRequest("v2")] * 2)
    register_worker("w1", "laptop", 123, max_calls=4)

    state = client.get("/api/system/queue").json()

    assert (state["queued"], state["running"]) == (2, 0)
    assert [w["id"] for w in state["workers"]] == ["w1"]


def test_fault_controls_are_refused_unless_enabled(client, monkeypatch):
    monkeypatch.delenv("SIMS_FAULT_INJECTION", raising=False)

    assert (
        client.put("/api/system/fail-rate", json={"fail_rate": 0.3}).status_code == 403
    )
    assert client.post("/api/system/workers/w1/kill").status_code == 403


def test_the_fail_rate_can_be_set_when_enabled(client, monkeypatch):
    monkeypatch.setenv("SIMS_FAULT_INJECTION", "1")

    client.put("/api/system/fail-rate", json={"fail_rate": 0.3})

    assert client.get("/api/system/queue").json()["fail_rate"] == 0.3


def test_killing_an_unknown_worker_is_404(client, monkeypatch):
    monkeypatch.setenv("SIMS_FAULT_INJECTION", "1")

    assert client.post("/api/system/workers/missing/kill").status_code == 404


def test_only_a_sims_worker_process_can_be_killed():
    assert not is_sims_worker_process(os.getpid())  # pytest, not a worker
    assert not is_sims_worker_process(999_999)  # no such process
