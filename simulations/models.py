import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from config import now


def new_id() -> str:
    return uuid.uuid4().hex[:8]


class SimulationStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Simulation(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
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


class SourceConversation(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    transcript: str
    reported_issue: str | None = None
    agent_version: str | None = None
    created_at: datetime = Field(default_factory=now)
