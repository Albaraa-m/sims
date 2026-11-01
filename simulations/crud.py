from sqlmodel import Session, SQLModel

from core import db
from simulations.models import (
    Simulation,
    SourceConversation,
    Test,
    TestSpec,
    TestStatus,
    new_id,
)


def save[Row: SQLModel](row: Row) -> Row:
    with Session(db.engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def _get[Row: SQLModel](model: type[Row], row_id: str) -> Row:
    with Session(db.engine) as session:
        return session.get_one(model, row_id)


def get_source_conversation(source_conversation_id: str) -> SourceConversation:
    return _get(SourceConversation, source_conversation_id)


def get_test(test_id: str) -> Test:
    return _get(Test, test_id)


def create_simulation(agent_version: str) -> Simulation:
    return save(Simulation(agent_version=agent_version))


def get_simulation(simulation_id: str) -> Simulation:
    return _get(Simulation, simulation_id)


def update_simulation(simulation_id: str, **changes) -> Simulation:
    simulation = _get(Simulation, simulation_id)
    for field, value in changes.items():
        setattr(simulation, field, value)
    return save(simulation)


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
    source_conversation: SourceConversation, spec: TestSpec
) -> Test:
    test_id = new_id()
    return save(
        Test(
            id=test_id,
            lineage_id=test_id,
            source_conversation_id=source_conversation.id,
            spec=spec.model_dump(),
            inferred=spec.model_dump(),
        )
    )


def edit_test(test_id: str, **changes) -> Test:
    """Saves the edit as a new draft version; earlier versions stay unchanged."""
    current = get_test(test_id)
    spec = TestSpec.model_validate({**current.spec, **changes})
    return save(
        Test(
            lineage_id=current.lineage_id,
            version=current.version + 1,
            source_conversation_id=current.source_conversation_id,
            spec=spec.model_dump(),
            inferred=current.inferred,
        )
    )


def mark_ready(test_id: str) -> Test:
    test = get_test(test_id)
    test.status = TestStatus.READY
    return save(test)
