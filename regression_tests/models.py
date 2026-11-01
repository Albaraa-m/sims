from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from core.config import now
from core.ids import new_id


class SourceConversation(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    transcript: str
    reported_issue: str | None = None
    agent_version: str | None = None
    created_at: datetime = Field(default_factory=now)


class TestSpec(BaseModel):
    # An unknown field is a typo or a model mistake, never something to drop silently.
    model_config = ConfigDict(extra="forbid")

    goal: str
    facts: dict[str, str]
    behavior: str
    policy_under_test: str
    expected_outcome: str


class TestStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class Test(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    lineage_id: str
    version: int = 1
    source_conversation_id: str = Field(foreign_key="sourceconversation.id")
    status: TestStatus = TestStatus.DRAFT
    spec: dict = Field(sa_column=Column(JSON))
    inferred: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)
