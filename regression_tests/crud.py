from sqlmodel import Session, col, func, select

from core import db
from core.db import get_row, save
from core.ids import new_id
from regression_tests.models import SourceConversation, Test, TestSpec, TestStatus


def get_source_conversation(source_conversation_id: str) -> SourceConversation:
    return get_row(SourceConversation, source_conversation_id)


def get_test(test_id: str) -> Test:
    return get_row(Test, test_id)


def save_transcript_as_source_conversation(
    transcript: str, reported_issue: str | None = None, agent_version: str | None = None
) -> SourceConversation:
    return save(
        SourceConversation(
            transcript=transcript,
            reported_issue=reported_issue,
            agent_version=agent_version,
        )
    )


def create_test_from_spec(
    source_conversation: SourceConversation,
    name: str,
    spec: TestSpec,
    inferred_spec: TestSpec | None = None,
) -> Test:
    """inferred_spec is what the model suggested, None if it found no broken rule."""
    test_id = new_id()
    return save(
        Test(
            id=test_id,
            lineage_id=test_id,
            name=name,
            source_conversation_id=source_conversation.id,
            spec=spec.model_dump(),
            inferred=inferred_spec.model_dump() if inferred_spec else None,
        )
    )


def create_test_from_transcript(
    transcript: str,
    reported_issue: str | None,
    agent_version: str | None,
    name: str,
    spec: TestSpec,
    inferred_spec: TestSpec | None,
) -> Test:
    source_conversation = save_transcript_as_source_conversation(
        transcript, reported_issue, agent_version
    )
    return create_test_from_spec(source_conversation, name, spec, inferred_spec)


def latest_version(lineage_id: str) -> int:
    with Session(db.engine) as session:
        query = select(func.max(Test.version)).where(Test.lineage_id == lineage_id)
        return session.exec(query).one() or 0


def edit_test(test_id: str, **changes) -> Test:
    """Saves the edit as a new draft version; earlier versions stay unchanged."""
    current = get_test(test_id)
    spec = TestSpec.model_validate({**current.spec, **changes})
    return save(
        Test(
            lineage_id=current.lineage_id,
            name=current.name,
            # Editing an older version still yields a new, unique latest version.
            version=latest_version(current.lineage_id) + 1,
            source_conversation_id=current.source_conversation_id,
            spec=spec.model_dump(),
            inferred=current.inferred,
        )
    )


def list_latest_tests() -> list[Test]:
    """The latest version of each test, newest test first."""
    with Session(db.engine) as session:
        latest = (
            select(Test.lineage_id, func.max(Test.version).label("version"))
            .group_by(col(Test.lineage_id))
            .subquery()
        )
        query = (
            select(Test)
            .join(
                latest,
                (col(Test.lineage_id) == latest.c.lineage_id)
                & (col(Test.version) == latest.c.version),
            )
            .order_by(col(Test.created_at).desc())
        )
        return list(session.exec(query))


def mark_ready(test_id: str) -> Test:
    test = get_test(test_id)
    test.status = TestStatus.READY
    return save(test)
