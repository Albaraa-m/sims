"""A worker claims queued runs, places their calls and grades them.

Run several, in separate processes: the queue's claim and lease keep them from taking
the same run, and each worker's reaper recovers runs whose worker died.
"""

import asyncio
import os
import random
import socket
import time

from evaluations.evaluate import evaluate_simulation
from evaluations.models import Outcome
from regression_tests.crud import get_test
from regression_tests.models import TestSpec
from regression_tests.run import build_caller_scenario
from simulations.models import Simulation, SimulationStatus
from simulations.queue import (
    MAX_CONCURRENT_CALLS,
    REAP_EVERY_SECONDS,
    claim_next_run,
    fail_attempt,
    finish_attempt_with_evidence,
    get_fail_rate,
    reap_expired_leases,
    renew_lease,
)
from simulations.runner import delete_room, run_call_attempt
from simulations.worker_registry import (
    record_worker_heartbeat,
    register_worker,
    unregister_worker,
)

POLL_SECONDS = 1
LEASE_RENEW_SECONDS = 10


class InjectedFailure(Exception):
    pass


def caller_scenario_of(simulation: Simulation) -> str | None:
    if simulation.test_id is None:
        return None
    return build_caller_scenario(
        TestSpec.model_validate(get_test(simulation.test_id).spec)
    )


async def keep_lease(simulation: Simulation, attempt_task: asyncio.Task) -> None:
    """Renews the lease while the attempt runs; stops the attempt once it isn't ours."""
    while True:
        await asyncio.sleep(LEASE_RENEW_SECONDS)
        if not renew_lease(simulation.id, simulation.attempt):
            attempt_task.cancel()
            return


async def work_on_attempt(simulation: Simulation, fail_rate: float) -> None:
    """Runs one claimed attempt to Done, a retry, or a give-up; never leaves it running."""
    attempt_task = asyncio.current_task()
    assert attempt_task is not None
    heartbeat = asyncio.create_task(keep_lease(simulation, attempt_task))
    try:
        if random.random() < fail_rate:
            raise InjectedFailure("injected failure (--fail-rate)")
        evidence = await run_call_attempt(simulation, caller_scenario_of(simulation))
    except asyncio.CancelledError:
        # Cancelled, or the lease was lost: someone else owns the run now.
        await delete_room(simulation.room_name)
        return
    # Any failure is logged on the run and retried; nothing may leave it running.
    except Exception as error:  # noqa: BLE001
        fail_attempt(
            simulation.id, simulation.attempt, str(error) or type(error).__name__
        )
        return
    finally:
        heartbeat.cancel()

    if not finish_attempt_with_evidence(simulation.id, simulation.attempt, **evidence):
        return
    evaluation = await evaluate_simulation(simulation.id)
    if evaluation.outcome == Outcome.EXECUTION_FAILED:
        # The call finished but can't be graded (e.g. the caller never spoke): retry it.
        fail_attempt(
            simulation.id,
            simulation.attempt,
            evaluation.reason,
            from_status=SimulationStatus.DONE,
        )


async def reap_and_close_rooms() -> None:
    for room in reap_expired_leases():
        await delete_room(room)


async def run_worker(
    worker_id: str,
    max_calls: int = MAX_CONCURRENT_CALLS,
    fail_rate: float = 0.0,
    stop: asyncio.Event | None = None,
) -> None:
    """fail_rate adds to the rate set from the website, for testing retries."""
    stop = stop or asyncio.Event()
    attempts: set[asyncio.Task] = set()
    next_reap = 0.0
    register_worker(worker_id, socket.gethostname(), os.getpid(), max_calls)
    try:
        while not stop.is_set():
            try:
                record_worker_heartbeat(worker_id, len(attempts))
                if time.monotonic() >= next_reap:
                    await reap_and_close_rooms()
                    next_reap = time.monotonic() + REAP_EVERY_SECONDS
                effective_fail_rate = max(fail_rate, get_fail_rate())
                while len(attempts) < max_calls:
                    simulation = claim_next_run(worker_id)
                    if simulation is None:
                        break
                    task = asyncio.create_task(
                        work_on_attempt(simulation, effective_fail_rate)
                    )
                    attempts.add(task)
                    task.add_done_callback(attempts.discard)
            # A busy database or a LiveKit hiccup must not stop the worker and its calls.
            except Exception as error:  # noqa: BLE001
                print(f"worker {worker_id}: loop error, retrying: {error}")
            await asyncio.sleep(POLL_SECONDS)
    finally:
        unregister_worker(worker_id)
        for task in attempts:
            task.cancel()
        await asyncio.gather(*attempts, return_exceptions=True)
