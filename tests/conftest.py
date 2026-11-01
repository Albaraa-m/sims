import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from core import db
from regression_tests.crud import save_transcript_as_source_conversation
from regression_tests.models import SourceConversation, TestSpec


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    monkeypatch.setattr(db, "engine", engine)
    SQLModel.metadata.create_all(engine)


@pytest.fixture
def spec() -> TestSpec:
    return TestSpec(
        goal="Book a table for 4 tonight at 19:00",
        facts={"name": "Dana", "party_size": "4", "time": "19:00"},
        behavior="Friendly and brief. Says yes if the details are read back.",
        may_vary=["name", "wording"],
        policy_under_test="Confirm details before booking",
        expected_outcome="Agent reads back the details and waits for a yes",
    )


@pytest.fixture
def source_conversation() -> SourceConversation:
    return save_transcript_as_source_conversation("Agent: Hi, how can I help?")
