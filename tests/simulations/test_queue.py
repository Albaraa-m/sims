from datetime import timedelta

import pytest

from core.config import now
from simulations.crud import get_simulation, update_simulation
from simulations.models import SimulationStatus
from simulations.queue import (
    MAX_QUEUED_RUNS,
    QueueFullError,
    RunRequest,
    admit_runs,
    cancel_runs,
    claim_next_run,
    fail_attempt,
    finish_attempt_with_evidence,
    get_fail_rate,
    list_refused_starts,
    reap_expired_leases,
    renew_lease,
    set_fail_rate,
)


def queue(count: int, swarm_id: str | None = None):
    return admit_runs([RunRequest("v2")] * count, swarm_id)


def test_admitted_runs_wait_as_queued():
    simulations = queue(3)

    assert [s.status for s in simulations] == [SimulationStatus.QUEUED] * 3


def test_a_start_that_overflows_the_queue_is_refused_whole():
    queue(MAX_QUEUED_RUNS - 1)

    with pytest.raises(QueueFullError):
        queue(2)
    assert claim_next_run("w", max_running=MAX_QUEUED_RUNS + 5) is not None


def test_claims_take_different_runs_oldest_first():
    first, second = queue(2)

    claimed = [claim_next_run("w1"), claim_next_run("w2")]

    assert [c.id for c in claimed if c] == [first.id, second.id]
    assert all(c and c.attempt == 1 for c in claimed)


def test_claims_stop_at_the_concurrency_cap():
    queue(3)

    claimed = [claim_next_run("w", max_running=2) for _ in range(3)]

    assert [c is not None for c in claimed] == [True, True, False]


def test_a_finished_attempt_is_done_with_its_evidence():
    [simulation] = queue(1)
    claim_next_run("w")

    assert finish_attempt_with_evidence(simulation.id, 1, {"chat_history": {}}, "a.ogg")
    done = get_simulation(simulation.id)
    assert done.status == SimulationStatus.DONE
    assert [entry["status"] for entry in done.attempts] == ["completed"]


def test_a_failed_attempt_is_retried_then_given_up():
    [simulation] = queue(1)
    for attempt in (1, 2, 3):
        claim_next_run("w")
        fail_attempt(simulation.id, attempt, "agent didn't join")

    failed = get_simulation(simulation.id)
    assert failed.status == SimulationStatus.FAILED
    assert [entry["attempt"] for entry in failed.attempts] == [1, 2, 3]


def test_a_late_write_from_an_old_attempt_changes_nothing():
    [simulation] = queue(1)
    claim_next_run("w1")
    fail_attempt(simulation.id, 1, "timed out")
    claim_next_run("w2")

    assert not finish_attempt_with_evidence(simulation.id, 1, {}, None)
    assert not renew_lease(simulation.id, 1)
    assert get_simulation(simulation.id).status == SimulationStatus.RUNNING


def test_an_expired_lease_is_interrupted_and_queued_again():
    [simulation] = queue(1)
    claim_next_run("w")
    update_simulation(simulation.id, lease_until=now() - timedelta(seconds=1))

    rooms = reap_expired_leases()

    assert rooms == [f"sim-{simulation.id}-1"]
    reaped = get_simulation(simulation.id)
    assert reaped.status == SimulationStatus.QUEUED
    assert reaped.attempts[0]["status"] == "interrupted"
    assert claim_next_run("w").attempt == 2  # type: ignore[union-attr]


def test_cancel_stops_waiting_and_running_calls():
    running, waiting = queue(2, swarm_id="s1")
    claim_next_run("w")

    rooms = cancel_runs("s1")

    assert rooms == [f"sim-{running.id}-1"]
    assert {get_simulation(s.id).status for s in (running, waiting)} == {
        SimulationStatus.CANCELLED
    }
    assert not finish_attempt_with_evidence(running.id, 1, {}, None)


def test_a_refused_start_is_recorded():
    queue(MAX_QUEUED_RUNS)

    with pytest.raises(QueueFullError):
        queue(1)

    [refused] = list_refused_starts(now() - timedelta(minutes=1))
    assert (refused.requested, refused.already_active) == (1, MAX_QUEUED_RUNS)


def test_the_fail_rate_is_shared_through_the_database():
    assert get_fail_rate() == 0.0

    set_fail_rate(0.3)

    assert get_fail_rate() == 0.3
