import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel

from config import now
from db import engine


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


def create_simulation(agent_version: str) -> Simulation:
    with Session(engine) as session:
        simulation = Simulation(agent_version=agent_version)
        session.add(simulation)
        session.commit()
        session.refresh(simulation)
        return simulation


def get_simulation(simulation_id: str) -> Simulation:
    with Session(engine) as session:
        return session.get_one(Simulation, simulation_id)


def update_simulation(simulation_id: str, **changes) -> Simulation:
    with Session(engine) as session:
        simulation = session.get_one(Simulation, simulation_id)
        for field, value in changes.items():
            setattr(simulation, field, value)
        session.add(simulation)
        session.commit()
        session.refresh(simulation)
        return simulation
