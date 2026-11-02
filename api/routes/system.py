"""Live state of the queue and its workers, and the fault controls used to show recovery."""

import os
import signal
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, func, select

from core import db
from core.config import now
from simulations import queue
from simulations.models import Simulation, SimulationStatus
from simulations.worker_registry import list_live_workers, unregister_worker

router = APIRouter(prefix="/api/system")


def fault_injection_enabled() -> bool:
    # Off unless the website is started for a demo; killing processes is not for daily use.
    return os.getenv("SIMS_FAULT_INJECTION") == "1"


def require_fault_injection() -> None:
    if not fault_injection_enabled():
        raise HTTPException(
            status_code=403,
            detail="fault injection is off; start the website with SIMS_FAULT_INJECTION=1",
        )


class WorkerRow(BaseModel):
    id: str
    host: str
    pid: int
    max_calls: int
    calls_running: int
    heartbeat_seconds_ago: float


class StoppedWorkerRow(BaseModel):
    """A worker that stopped heartbeating while still holding running simulations."""

    id: str
    simulations_recovering: int
    # At most this long until a live worker's reaper puts them back in the queue.
    seconds_until_requeued: float


class QueueState(BaseModel):
    queued: int
    running: int
    max_running: int
    max_queued: int
    # How long the simulation waiting longest has been waiting since it was requested.
    longest_wait_seconds: float | None
    fail_rate: float
    fault_injection_enabled: bool
    refused_starts_last_hour: int
    # Every simulation ever refused by admission, so the ledger of requests adds up.
    refused_simulations: int
    workers: list[WorkerRow]
    stopped_workers: list[StoppedWorkerRow]


class FailRate(BaseModel):
    fail_rate: float = Field(ge=0, le=1)


def count_runs_with_status(status: SimulationStatus) -> int:
    with Session(db.engine) as session:
        query = (
            select(func.count())
            .select_from(Simulation)
            .where(Simulation.status == status)
        )
        return session.exec(query).one()


def read_longest_wait_seconds(moment: datetime) -> float | None:
    with Session(db.engine) as session:
        query = select(func.min(Simulation.started_at)).where(
            Simulation.status == SimulationStatus.QUEUED
        )
        oldest_started_at = session.exec(query).one()
    if oldest_started_at is None:
        return None
    return (moment - oldest_started_at.replace(tzinfo=moment.tzinfo)).total_seconds()


def list_stopped_workers_holding_simulations(
    live_worker_ids: set[str], moment: datetime
) -> list[StoppedWorkerRow]:
    with Session(db.engine) as session:
        query = select(Simulation).where(
            Simulation.status == SimulationStatus.RUNNING,
            col(Simulation.worker_id).is_not(None),
            col(Simulation.worker_id).not_in(live_worker_ids),
        )
        orphaned = list(session.exec(query))
    leases_by_worker: dict[str, list[datetime]] = defaultdict(list)
    for simulation in orphaned:
        assert simulation.worker_id is not None
        lease_until = simulation.lease_until or moment
        leases_by_worker[simulation.worker_id].append(
            lease_until.replace(tzinfo=moment.tzinfo)
        )
    return [
        StoppedWorkerRow(
            id=worker_id,
            simulations_recovering=len(leases),
            seconds_until_requeued=max(0.0, (max(leases) - moment).total_seconds())
            + queue.REAP_EVERY_SECONDS,
        )
        for worker_id, leases in sorted(leases_by_worker.items())
    ]


@router.get("/queue")
def read_queue_state() -> QueueState:
    moment = now()
    live_workers = list_live_workers()
    return QueueState(
        queued=count_runs_with_status(SimulationStatus.QUEUED),
        running=count_runs_with_status(SimulationStatus.RUNNING),
        max_running=queue.MAX_CONCURRENT_CALLS,
        max_queued=queue.MAX_QUEUED_RUNS,
        longest_wait_seconds=read_longest_wait_seconds(moment),
        fail_rate=queue.get_fail_rate(),
        fault_injection_enabled=fault_injection_enabled(),
        refused_starts_last_hour=len(
            queue.list_refused_starts(moment - timedelta(hours=1))
        ),
        refused_simulations=queue.count_refused_simulations(),
        stopped_workers=list_stopped_workers_holding_simulations(
            {worker.id for worker in live_workers}, moment
        ),
        workers=[
            WorkerRow(
                id=worker.id,
                host=worker.host,
                pid=worker.pid,
                max_calls=worker.max_calls,
                calls_running=worker.calls_running,
                heartbeat_seconds_ago=(
                    moment - worker.heartbeat_at.replace(tzinfo=moment.tzinfo)
                ).total_seconds(),
            )
            for worker in live_workers
        ],
    )


def is_sims_worker_process(pid: int) -> bool:
    """Guards the kill: the process must exist here and be a sims worker. Hostnames
    can't be compared, as macOS reports different ones to different processes."""
    command = subprocess.run(
        ["ps", "-o", "command=", "-p", str(pid)],
        check=False,
        capture_output=True,
        text=True,
    ).stdout
    return "sims" in command and "worker" in command


@router.post("/workers/{worker_id}/kill")
def kill_worker(worker_id: str) -> None:
    """Kills the worker's process outright, as a crash would; its calls are recovered."""
    require_fault_injection()
    worker = next((w for w in list_live_workers() if w.id == worker_id), None)
    if worker is None:
        raise HTTPException(
            status_code=404, detail=f"worker {worker_id} is not running"
        )
    if not is_sims_worker_process(worker.pid):
        raise HTTPException(
            status_code=409,
            detail=f"process {worker.pid} isn't a sims worker on this machine",
        )
    os.kill(worker.pid, signal.SIGKILL)
    unregister_worker(worker.id)


@router.put("/fail-rate")
def set_fail_rate(request: FailRate) -> FailRate:
    require_fault_injection()
    queue.set_fail_rate(request.fail_rate)
    return request
