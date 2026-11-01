from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from core.config import now
from core.ids import new_id


class Outcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    EXECUTION_FAILED = "execution_failed"
    INCONCLUSIVE = "inconclusive"


class Evaluation(SQLModel, table=True):
    """One grading of one simulation; regrading adds a row and never overwrites."""

    id: str = Field(default_factory=new_id, primary_key=True)
    simulation_id: str = Field(foreign_key="simulation.id", index=True)
    outcome: Outcome
    # None when the judge wasn't asked, e.g. for an execution failure.
    situation_happened: bool | None = None
    cited_turns: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    reason: str
    judge_model: str | None = None
    judge_prompt_version: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=now)
