from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from evaluations.models import Outcome
from regression_tests.models import TestSpec, TestStatus
from simulations.conversation import SpokenLine, ToolCall
from simulations.models import SimulationStatus


class InferTestRequest(BaseModel):
    transcript: str
    reported_issue: str | None = None


class InferTestResponse(BaseModel):
    reason: str
    name: str | None
    spec: TestSpec | None


class CreateTestRequest(BaseModel):
    transcript: str
    reported_issue: str | None = None
    agent_version: str | None = None
    name: str
    spec: TestSpec
    inferred_spec: TestSpec | None = None


class EditTestRequest(BaseModel):
    name: str
    spec: TestSpec


class StartRunsRequest(BaseModel):
    agent_versions: list[Literal["v1", "v2"]] = Field(min_length=1)
    runs_per_version: int = Field(default=1, ge=1, le=5)


def mark_as_utc(time: datetime | None) -> datetime | None:
    # SQLite drops the timezone; every stored time is UTC.
    return time and time.replace(tzinfo=UTC)


class RunRow(BaseModel):
    id: str
    test_id: str
    test_name: str
    test_version: int
    agent_version: str
    status: SimulationStatus
    started_at: datetime
    ended_at: datetime | None
    # None until the run is graded.
    outcome: Outcome | None

    _mark_times_as_utc = field_validator("started_at", "ended_at")(mark_as_utc)


class EvaluationDetail(BaseModel):
    outcome: Outcome
    situation_happened: bool | None
    cited_turns: list[int]
    reason: str
    judge_model: str | None
    judge_prompt_version: str | None
    error: str | None
    created_at: datetime

    _mark_created_at_as_utc = field_validator("created_at")(mark_as_utc)


class TestRow(BaseModel):
    id: str
    name: str
    version: int
    status: TestStatus
    created_at: datetime

    _mark_created_at_as_utc = field_validator("created_at")(mark_as_utc)


class TestDetail(TestRow):
    spec: TestSpec
    # What the model suggested; None if it found no broken rule.
    inferred: TestSpec | None


class RunDetail(BaseModel):
    id: str
    agent_version: str
    status: SimulationStatus
    started_at: datetime
    ended_at: datetime | None
    error: str | None
    # None for runs started outside a test, e.g. with `sims run`.
    test_id: str | None
    test_name: str | None
    test_version: int | None
    conversation: list[SpokenLine | ToolCall]
    has_recording: bool
    # Newest first; the first one is the run's current outcome.
    evaluations: list[EvaluationDetail]

    _mark_times_as_utc = field_validator("started_at", "ended_at")(mark_as_utc)
