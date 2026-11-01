from datetime import datetime

from pydantic import BaseModel

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


class TestRow(BaseModel):
    id: str
    name: str
    version: int
    status: TestStatus
    created_at: datetime
