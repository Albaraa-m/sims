from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from core.config import now
from core.ids import new_id
from regression_tests.models import TestSpec


class Swarm(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    agent_version: str
    # Every policy found in the agent's instructions, including untested ones.
    policies: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)


class Policy(BaseModel):
    """A rule found in the agent's instructions; each becomes one test."""

    # Reads like a test name: "Agent refers parties over 8 to the events team".
    name: str
    rule: str


class Scenario(BaseModel):
    """One generated test: name is its short label, spec.behavior the caller instruction."""

    name: str
    spec: TestSpec
