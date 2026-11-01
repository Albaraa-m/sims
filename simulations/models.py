import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel
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


class TestSpec(BaseModel):
    __test__ = False  # stops pytest collecting this class as a test case

    goal: str
    facts: dict[str, str]
    behavior: str
    policy_under_test: str
    expected_outcome: str
    fixed: list[str]
    varying: list[str]


class TestStatus(StrEnum):
    __test__ = False  # stops pytest collecting this class as a test case

    DRAFT = "draft"
    READY = "ready"


class Test(SQLModel, table=True):
    __test__ = False  # stops pytest collecting this class as a test case

    id: str = Field(default_factory=new_id, primary_key=True)
    lineage_id: str
    version: int = 1
    source_conversation_id: str = Field(foreign_key="sourceconversation.id")
    status: TestStatus = TestStatus.DRAFT
    spec: dict = Field(sa_column=Column(JSON))
    inferred: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)
