"""The run queue: simulation rows, claimed by workers under a time-limited lease.

Every write that finishes an attempt checks the row is still running that attempt, so
a worker that comes back late can't overwrite a retry or a cancel.
"""

import os
from datetime import datetime, timedelta
from typing import NamedTuple

from sqlalchemy import CursorResult, func, update
from sqlmodel import Session, col, select

from core import db
from core.config import now
from simulations.models import (
    QueueSettings,
    RefusedStart,
    Simulation,
    SimulationStatus,
)

# Overridable from the environment, so a load test can show admission at a small cap.
MAX_QUEUED_RUNS = int(os.getenv("SIMS_MAX_QUEUED_RUNS", "50"))
# Each call holds 2 agent sessions; the Ship plan allows 20 inference connections per
# model, and the laptop runs both agents of every call.
MAX_CONCURRENT_CALLS = int(os.getenv("SIMS_MAX_CONCURRENT_CALLS", "4"))
LEASE_SECONDS = 60
# How often each worker looks for expired leases; a dead worker's calls wait at most
# LEASE_SECONDS plus this before going back in the queue.
REAP_EVERY_SECONDS = 15


class QueueFullError(Exception):
    pass


class RunRequest(NamedTuple):
    agent_version: str
    test_id: str | None = None


def count_active_runs(session: Session) -> int:
    query = (
        select(func.count())
        .select_from(Simulation)
        .where(
            col(Simulation.status).in_(
                [SimulationStatus.QUEUED, SimulationStatus.RUNNING]
            )
        )
    )
    return session.exec(query).one()


def admit_runs(
    requests: list[RunRequest],
    swarm_id: str | None = None,
    swarm_run_id: str | None = None,
) -> list[Simulation]:
    """Queues every request, or none: a start that doesn't fit is refused whole."""
    with Session(db.engine) as session:
        active = count_active_runs(session)
        if active + len(requests) > MAX_QUEUED_RUNS:
            session.add(
                RefusedStart(
                    requested=len(requests), already_active=active, swarm_id=swarm_id
                )
            )
            session.commit()
            raise QueueFullError(
                f"{len(requests)} runs would exceed the queue limit of "
                f"{MAX_QUEUED_RUNS} ({active} already waiting or running)"
            )
        simulations = [
            Simulation(
                agent_version=request.agent_version,
                test_id=request.test_id,
                swarm_id=swarm_id,
                swarm_run_id=swarm_run_id,
            )
            for request in requests
        ]
        session.add_all(simulations)
        session.commit()
        for simulation in simulations:
            session.refresh(simulation)
        return simulations


def claim_next_run(
    worker_id: str, max_running: int = MAX_CONCURRENT_CALLS
) -> Simulation | None:
    """Takes the oldest queued run as its next attempt, if fewer than max_running run.

    One UPDATE, so two workers can never claim the same row or push past the cap.
    """
    oldest_queued = (
        select(Simulation.id)
        .where(Simulation.status == SimulationStatus.QUEUED)
        .order_by(col(Simulation.started_at))
        .limit(1)
        .scalar_subquery()
    )
    running = (
        select(func.count())
        .select_from(Simulation)
        .where(Simulation.status == SimulationStatus.RUNNING)
        .scalar_subquery()
    )
    claim = (
        update(Simulation)
        .where(
            col(Simulation.id) == oldest_queued,
            col(Simulation.status) == SimulationStatus.QUEUED,
            running < max_running,
        )
        .values(
            status=SimulationStatus.RUNNING,
            attempt=col(Simulation.attempt) + 1,
            worker_id=worker_id,
            lease_until=now() + timedelta(seconds=LEASE_SECONDS),
            call_started_at=now(),
            ended_at=None,
        )
        .returning(col(Simulation.id))
    )
    with Session(db.engine) as session:
        claimed_id = session.exec(claim).scalar_one_or_none()  # type: ignore[call-overload]
        session.commit()
        return session.get(Simulation, claimed_id) if claimed_id else None


def update_running_attempt(
    session: Session, simulation_id: str, attempt: int, **values
) -> bool:
    """Applies values only if the row is still running that attempt."""
    guarded = (
        update(Simulation)
        .where(
            col(Simulation.id) == simulation_id,
            col(Simulation.status) == SimulationStatus.RUNNING,
            col(Simulation.attempt) == attempt,
        )
        .values(**values)
    )
    result: CursorResult = session.exec(guarded)  # type: ignore[call-overload]
    session.commit()
    return result.rowcount == 1


def renew_lease(simulation_id: str, attempt: int) -> bool:
    """False once the attempt is no longer this worker's, e.g. after a cancel."""
    with Session(db.engine) as session:
        return update_running_attempt(
            session,
            simulation_id,
            attempt,
            lease_until=now() + timedelta(seconds=LEASE_SECONDS),
        )


def attempt_log_entry(simulation: Simulation, status: str, reason: str | None) -> dict:
    started_at = simulation.call_started_at
    return {
        "attempt": simulation.attempt,
        "status": status,
        "reason": reason,
        "started_at": started_at.isoformat() if started_at else None,
        "ended_at": now().isoformat(),
    }


def finish_attempt_with_evidence(
    simulation_id: str, attempt: int, report: dict, recording_path: str | None
) -> bool:
    with Session(db.engine) as session:
        simulation = session.get_one(Simulation, simulation_id)
        entry = attempt_log_entry(simulation, "completed", None)
        return update_running_attempt(
            session,
            simulation_id,
            attempt,
            status=SimulationStatus.DONE,
            report=report,
            recording_path=recording_path,
            error=None,
            lease_until=None,
            ended_at=now(),
            attempts=[*simulation.attempts, entry],
        )


def fail_attempt(
    simulation_id: str,
    attempt: int,
    reason: str,
    attempt_status: str = "failed",
    from_status: SimulationStatus = SimulationStatus.RUNNING,
) -> bool:
    """Logs the attempt, then queues the next one, or marks the run failed after the last.

    from_status is DONE when a finished call is graded as an execution failure.
    """
    with Session(db.engine) as session:
        simulation = session.get_one(Simulation, simulation_id)
        if simulation.status != from_status or simulation.attempt != attempt:
            return False
        entry = attempt_log_entry(simulation, attempt_status, reason)
        is_last = attempt >= simulation.max_attempts
        guarded = (
            update(Simulation)
            .where(
                col(Simulation.id) == simulation_id,
                col(Simulation.status) == from_status,
                col(Simulation.attempt) == attempt,
            )
            .values(
                status=SimulationStatus.FAILED if is_last else SimulationStatus.QUEUED,
                error=reason,
                worker_id=None,
                lease_until=None,
                ended_at=now() if is_last else None,
                attempts=[*simulation.attempts, entry],
            )
        )
        result: CursorResult = session.exec(guarded)  # type: ignore[call-overload]
        session.commit()
        return result.rowcount == 1


def room_of_attempt(simulation_id: str, attempt: int) -> str:
    return f"sim-{simulation_id}-{attempt}"


def reap_expired_leases() -> list[str]:
    """Interrupts running attempts whose worker stopped renewing; returns their rooms."""
    with Session(db.engine) as session:
        query = select(Simulation).where(
            Simulation.status == SimulationStatus.RUNNING,
            col(Simulation.lease_until) < now(),
        )
        expired = list(session.exec(query))
    rooms = []
    for simulation in expired:
        if fail_attempt(
            simulation.id,
            simulation.attempt,
            "worker lost: its lease expired",
            attempt_status="interrupted",
        ):
            rooms.append(room_of_attempt(simulation.id, simulation.attempt))
    return rooms


def cancel_runs(swarm_id: str, swarm_run_id: str | None = None) -> list[str]:
    """Cancels the waiting and running calls of a swarm, or of one of its runs;
    returns the rooms to close."""
    with Session(db.engine) as session:
        query = select(Simulation).where(
            Simulation.swarm_id == swarm_id,
            col(Simulation.status).in_(
                [SimulationStatus.QUEUED, SimulationStatus.RUNNING]
            ),
        )
        if swarm_run_id is not None:
            query = query.where(Simulation.swarm_run_id == swarm_run_id)
        active = list(session.exec(query))
        rooms = [
            room_of_attempt(simulation.id, simulation.attempt)
            for simulation in active
            if simulation.status == SimulationStatus.RUNNING
        ]
        for simulation in active:
            simulation.status = SimulationStatus.CANCELLED
            simulation.lease_until = None
            simulation.ended_at = now()
            session.add(simulation)
        session.commit()
    return rooms


def get_fail_rate() -> float:
    with Session(db.engine) as session:
        settings = session.get(QueueSettings, 1)
        return settings.fail_rate if settings else 0.0


def set_fail_rate(fail_rate: float) -> None:
    with Session(db.engine) as session:
        settings = session.get(QueueSettings, 1) or QueueSettings()
        settings.fail_rate = fail_rate
        session.add(settings)
        session.commit()


def list_refused_starts(since: datetime) -> list[RefusedStart]:
    with Session(db.engine) as session:
        query = (
            select(RefusedStart)
            .where(col(RefusedStart.refused_at) >= since)
            .order_by(col(RefusedStart.refused_at).desc())
        )
        return list(session.exec(query))


def count_refused_simulations() -> int:
    with Session(db.engine) as session:
        query = select(func.coalesce(func.sum(RefusedStart.requested), 0))
        return session.exec(query).one()
