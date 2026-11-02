from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from evaluations.execution import ExecutionFailureKind
from evaluations.models import Outcome
from regression_tests.models import TestSpec, TestStatus
from simulations.conversation import SpokenLine, ToolCall
from simulations.models import SimulationStatus
from swarms.models import Policy, Scenario


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


class QueuedRuns(BaseModel):
    queued: int
    swarm_run_id: str | None = None
    swarm_run_number: int | None = None


def mark_as_utc(time: datetime | None) -> datetime | None:
    # SQLite drops the timezone; every stored time is UTC.
    return time and time.replace(tzinfo=UTC)


class AttemptLogEntry(BaseModel):
    attempt: int
    # completed, failed or interrupted
    status: str
    reason: str | None
    started_at: datetime | None
    ended_at: datetime | None

    _mark_times_as_utc = field_validator("started_at", "ended_at")(mark_as_utc)


class RunRow(BaseModel):
    id: str
    test_id: str
    # Shared by every version of the test, so a test can be counted once.
    test_lineage_id: str
    test_name: str
    test_version: int
    agent_version: str
    status: SimulationStatus
    # The current attempt, 0 while queued for the first time; past ones are in attempts.
    attempt: int
    attempts: list[AttemptLogEntry]
    # started_at is when the run was requested; call_started_at, when its attempt began.
    started_at: datetime
    call_started_at: datetime | None
    ended_at: datetime | None
    # None until the latest attempt is done and graded.
    outcome: Outcome | None
    reason: str | None
    judge_model: str | None
    judge_prompt_version: str | None
    # Set only for execution failures, so they can be grouped.
    execution_failure_kind: ExecutionFailureKind | None

    _mark_times_as_utc = field_validator("started_at", "call_started_at", "ended_at")(
        mark_as_utc
    )


class EvaluationDetail(BaseModel):
    outcome: Outcome
    situation_happened: bool | None
    cited_turns: list[int]
    reason: str
    reasoning: str | None
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
    # Set for generated tests; None for tests made from a transcript.
    swarm_id: str | None
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
    attempt: int
    max_attempts: int
    attempts: list[AttemptLogEntry]
    started_at: datetime
    call_started_at: datetime | None
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

    _mark_times_as_utc = field_validator("started_at", "call_started_at", "ended_at")(
        mark_as_utc
    )


class FindPoliciesRequest(BaseModel):
    agent_version: Literal["v1", "v2"]


class FoundPolicies(BaseModel):
    agent_version: str
    policies: list[Policy]


class GenerateSwarmRequest(BaseModel):
    agent_version: Literal["v1", "v2"]
    # The policies the reviewer ticked; each gets one test.
    policies: list[Policy] = Field(min_length=1)


class SaveSwarmRequest(BaseModel):
    name: str = Field(min_length=1)
    agent_version: Literal["v1", "v2"]
    policies: list[str]
    scenarios: list[Scenario] = Field(min_length=1)


class SwarmRow(BaseModel):
    id: str
    name: str
    agent_version: str
    test_count: int
    created_at: datetime

    _mark_created_at_as_utc = field_validator("created_at")(mark_as_utc)


class SwarmTest(BaseModel):
    id: str
    name: str
    version: int
    status: TestStatus
    spec: TestSpec


class SwarmDetail(SwarmRow):
    # Every policy found, so untested ones show too; tests group by policy_under_test.
    policies: list[str]
    tests: list[SwarmTest]


class SwarmRunSummary(BaseModel):
    # "earlier" for calls queued before runs were numbered.
    id: str
    number: int
    created_at: datetime | None
    agent_versions: list[str]
    # Worked out from its calls: queued, running, completed or cancelled.
    status: Literal["queued", "running", "completed", "cancelled"]
    total: int
    status_counts: dict[str, int]
    outcome_counts: dict[str, int]

    _mark_created_at_as_utc = field_validator("created_at")(mark_as_utc)
