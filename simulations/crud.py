from sqlmodel import Session, SQLModel

import db
from simulations.models import Simulation, SourceConversation


def save[Row: SQLModel](row: Row) -> Row:
    with Session(db.engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get[Row: SQLModel](model: type[Row], row_id: str) -> Row:
    with Session(db.engine) as session:
        return session.get_one(model, row_id)


def create_simulation(agent_version: str) -> Simulation:
    return save(Simulation(agent_version=agent_version))


def get_simulation(simulation_id: str) -> Simulation:
    return get(Simulation, simulation_id)


def update_simulation(simulation_id: str, **changes) -> Simulation:
    simulation = get(Simulation, simulation_id)
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
