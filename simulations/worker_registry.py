"""Workers record themselves here, so the website can list them and stop one."""

from datetime import timedelta

from sqlmodel import Session, col, select

from core import db
from core.config import now
from core.db import save
from simulations.models import WorkerProcess

# A few missed heartbeats (one per loop, about a second apart) means the worker is gone.
HEARTBEAT_TIMEOUT_SECONDS = 10


def register_worker(worker_id: str, pid: int, max_calls: int) -> None:
    save(WorkerProcess(id=worker_id, pid=pid, max_calls=max_calls))


def record_worker_heartbeat(worker_id: str, calls_running: int) -> None:
    with Session(db.engine) as session:
        worker = session.get(WorkerProcess, worker_id)
        if worker is None:
            return
        worker.calls_running = calls_running
        worker.heartbeat_at = now()
        session.add(worker)
        session.commit()


def unregister_worker(worker_id: str) -> None:
    with Session(db.engine) as session:
        worker = session.get(WorkerProcess, worker_id)
        if worker is not None:
            session.delete(worker)
            session.commit()


def list_live_workers() -> list[WorkerProcess]:
    """Workers with a recent heartbeat; dead workers' rows are dropped on the way."""
    cutoff = now() - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
    # The listed workers are read after the commit that drops the dead ones.
    with Session(db.engine, expire_on_commit=False) as session:
        workers = list(
            session.exec(select(WorkerProcess).order_by(col(WorkerProcess.started_at)))
        )
        live = [
            w for w in workers if w.heartbeat_at.replace(tzinfo=cutoff.tzinfo) >= cutoff
        ]
        for worker in workers:
            if worker not in live:
                session.delete(worker)
        session.commit()
        return live
