import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from sqlalchemy import JSON, Column, event
from sqlmodel import Field, Session, SQLModel, create_engine

DB_PATH = Path(__file__).parent / "sims.db"

engine = create_engine(f"sqlite:///{DB_PATH}")


@event.listens_for(engine, "connect")
def use_write_ahead_log(connection, _) -> None:
    # call.py and the booking agent write to the same file from different processes.
    connection.execute("PRAGMA journal_mode=WAL")


def now() -> datetime:
    return datetime.now(UTC)


class SimulationStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Simulation(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8], primary_key=True)
    test_id: str | None = None
    agent_version: str
    status: SimulationStatus = SimulationStatus.RUNNING
    report: dict | None = Field(default=None, sa_column=Column(JSON))
    recording_path: str | None = None
    error: str | None = None
    started_at: datetime = Field(default_factory=now)
    ended_at: datetime | None = None

    @property
    def room_name(self) -> str:
        return f"sim-{self.id}"


SQLModel.metadata.create_all(engine)


def update_simulation(simulation_id: str, **changes) -> Simulation:
    with Session(engine) as session:
        simulation = session.get_one(Simulation, simulation_id)
        for field, value in changes.items():
            setattr(simulation, field, value)
        session.add(simulation)
        session.commit()
        session.refresh(simulation)
        return simulation
