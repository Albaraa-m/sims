from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from core.config import now
from core.ids import new_id

MAX_ATTEMPTS = 3


class SimulationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    # No usable call after every attempt; says nothing about the agent.
    FAILED = "failed"
    CANCELLED = "cancelled"


class Simulation(SQLModel, table=True):
    """One requested call. A retry is the next attempt on the same row, so a call is
    never counted twice; each attempt's outcome is kept in attempts."""

    id: str = Field(default_factory=new_id, primary_key=True)
    test_id: str | None = None
    swarm_id: str | None = Field(default=None, index=True)
    agent_version: str
    status: SimulationStatus = SimulationStatus.QUEUED
    # The current attempt, from 1; 0 while it has never been claimed.
    attempt: int = Field(default=0, sa_column_kwargs={"server_default": "1"})
    max_attempts: int = Field(
        default=MAX_ATTEMPTS, sa_column_kwargs={"server_default": str(MAX_ATTEMPTS)}
    )
    worker_id: str | None = None
    # The worker owns the running attempt until then; past it, the reaper takes over.
    lease_until: datetime | None = None
    # One entry per finished attempt: {attempt, status, reason, started_at, ended_at}.
    attempts: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    report: dict | None = Field(default=None, sa_column=Column(JSON))
    recording_path: str | None = None
    error: str | None = None
    # When the call was requested; the current attempt's start is call_started_at.
    started_at: datetime = Field(default_factory=now)
    call_started_at: datetime | None = None
    ended_at: datetime | None = None

    @property
    def room_name(self) -> str:
        # One room per attempt, so a retry never shares a room with a dead attempt's agents.
        return f"sim-{self.id}-{self.attempt}"
