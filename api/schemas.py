from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from regression_tests.models import TestSpec, TestStatus


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


class TestRow(BaseModel):
    id: str
    name: str
    version: int
    status: TestStatus
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def mark_as_utc(cls, created_at: datetime) -> datetime:
        # SQLite drops the timezone; every stored time is UTC.
        return created_at.replace(tzinfo=UTC)


class TestDetail(TestRow):
    spec: TestSpec
    # What the model suggested; None if it found no broken rule.
    inferred: TestSpec | None
