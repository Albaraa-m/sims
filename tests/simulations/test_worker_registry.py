from datetime import timedelta

from core.config import now
from core.db import get_row, save
from simulations.models import WorkerProcess
from simulations.worker_registry import (
    list_live_workers,
    record_worker_heartbeat,
    register_worker,
    unregister_worker,
)


def test_a_registered_worker_is_listed_with_its_calls():
    register_worker("w1", "laptop", 123, max_calls=4)
    record_worker_heartbeat("w1", calls_running=3)

    [worker] = list_live_workers()

    assert (worker.id, worker.calls_running) == ("w1", 3)


def test_a_worker_without_recent_heartbeats_is_dropped():
    register_worker("w1", "laptop", 123, max_calls=4)
    worker = get_row(WorkerProcess, "w1")
    worker.heartbeat_at = now() - timedelta(minutes=1)
    save(worker)

    assert list_live_workers() == []


def test_a_stopped_worker_is_removed():
    register_worker("w1", "laptop", 123, max_calls=4)

    unregister_worker("w1")

    assert list_live_workers() == []
