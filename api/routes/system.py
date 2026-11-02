"""Live state of the queue and its workers, and the fault controls used to show recovery."""

import os
import signal
import socket
from datetime import timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

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


class QueueState(BaseModel):
    queued: int
    running: int
    max_running: int
    max_queued: int
    fail_rate: float
    fault_injection_enabled: bool
    refused_starts_last_hour: int
    workers: list[WorkerRow]


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


@router.get("/queue")
def read_queue_state() -> QueueState:
    moment = now()
    return QueueState(
        queued=count_runs_with_status(SimulationStatus.QUEUED),
        running=count_runs_with_status(SimulationStatus.RUNNING),
        max_running=queue.MAX_CONCURRENT_CALLS,
        max_queued=queue.MAX_QUEUED_RUNS,
        fail_rate=queue.get_fail_rate(),
        fault_injection_enabled=fault_injection_enabled(),
        refused_starts_last_hour=len(
            queue.list_refused_starts(moment - timedelta(hours=1))
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
            for worker in list_live_workers()
        ],
    )


@router.post("/workers/{worker_id}/kill")
def kill_worker(worker_id: str) -> None:
    """Kills the worker's process outright, as a crash would; its calls are recovered."""
    require_fault_injection()
    worker = next((w for w in list_live_workers() if w.id == worker_id), None)
    if worker is None:
        raise HTTPException(
            status_code=404, detail=f"worker {worker_id} is not running"
        )
    if worker.host != socket.gethostname():
        raise HTTPException(
            status_code=409, detail="the worker runs on another machine"
        )
    os.kill(worker.pid, signal.SIGKILL)
    unregister_worker(worker.id)


@router.put("/fail-rate")
def set_fail_rate(request: FailRate) -> FailRate:
    require_fault_injection()
    queue.set_fail_rate(request.fail_rate)
    return request
