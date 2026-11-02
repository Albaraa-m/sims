import asyncio

import pytest

from evaluations.models import Evaluation, Outcome
from simulations import worker
from simulations.crud import get_simulation
from simulations.models import SimulationStatus
from simulations.queue import RunRequest, admit_runs

EVIDENCE = {"report": {"chat_history": {}}, "recording_path": "a.ogg"}


@pytest.fixture(autouse=True)
def fast_worker(monkeypatch):
    monkeypatch.setattr(worker, "POLL_SECONDS", 0.01)

    async def no_room_to_delete(_room: str) -> None:
        pass

    monkeypatch.setattr(worker, "delete_room", no_room_to_delete)


def fake_calls(monkeypatch, results: list) -> list[int]:
    """Each attempt's call raises or returns the next result; returns attempts seen."""
    seen: list[int] = []

    async def fake_run_call_attempt(simulation, _scenario):
        seen.append(simulation.attempt)
        result = results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(worker, "run_call_attempt", fake_run_call_attempt)
    return seen


def fake_grades(monkeypatch, outcomes: list[Outcome]) -> None:
    async def fake_evaluate_simulation(simulation_id: str) -> Evaluation:
        return Evaluation(
            simulation_id=simulation_id, outcome=outcomes.pop(0), reason="r"
        )

    monkeypatch.setattr(worker, "evaluate_simulation", fake_evaluate_simulation)


def run_until_settled(simulation_ids: list[str], max_calls: int = 4) -> None:
    async def run() -> None:
        stop = asyncio.Event()
        task = asyncio.create_task(worker.run_worker("w", max_calls, stop=stop))
        while any(
            get_simulation(i).status
            in (SimulationStatus.QUEUED, SimulationStatus.RUNNING)
            for i in simulation_ids
        ):
            await asyncio.sleep(0.01)
        stop.set()
        await task

    asyncio.run(asyncio.wait_for(run(), timeout=5))


def test_failed_attempts_are_retried_until_one_succeeds(monkeypatch):
    seen = fake_calls(
        monkeypatch, [RuntimeError("no agent"), RuntimeError("no agent"), EVIDENCE]
    )
    fake_grades(monkeypatch, [Outcome.PASS])
    [simulation] = admit_runs([RunRequest("v2")])

    run_until_settled([simulation.id])

    done = get_simulation(simulation.id)
    assert seen == [1, 2, 3]
    assert done.status == SimulationStatus.DONE
    assert [e["status"] for e in done.attempts] == ["failed", "failed", "completed"]


def test_an_ungradable_call_is_retried(monkeypatch):
    fake_calls(monkeypatch, [EVIDENCE, EVIDENCE])
    fake_grades(monkeypatch, [Outcome.EXECUTION_FAILED, Outcome.FAIL])
    [simulation] = admit_runs([RunRequest("v2")])

    run_until_settled([simulation.id])

    done = get_simulation(simulation.id)
    assert (done.status, done.attempt) == (SimulationStatus.DONE, 2)


def test_a_run_that_never_gets_a_call_is_given_up(monkeypatch):
    fake_calls(monkeypatch, [RuntimeError("no agent")] * 3)
    [simulation] = admit_runs([RunRequest("v2")])

    run_until_settled([simulation.id])

    assert get_simulation(simulation.id).status == SimulationStatus.FAILED


def test_the_worker_never_runs_more_calls_than_its_limit(monkeypatch):
    running, peak = 0, 0

    async def slow_call(_simulation, _scenario):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.05)
        running -= 1
        return EVIDENCE

    monkeypatch.setattr(worker, "run_call_attempt", slow_call)
    fake_grades(monkeypatch, [Outcome.PASS] * 6)
    simulations = admit_runs([RunRequest("v2")] * 6)

    run_until_settled([s.id for s in simulations], max_calls=2)

    assert peak == 2
