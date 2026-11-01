from sqlmodel import Session, col, select

from core import db
from evaluations.models import Evaluation


def list_evaluations_of_simulation(simulation_id: str) -> list[Evaluation]:
    """Newest first."""
    with Session(db.engine) as session:
        query = (
            select(Evaluation)
            .where(Evaluation.simulation_id == simulation_id)
            .order_by(col(Evaluation.created_at).desc())
        )
        return list(session.exec(query).all())


def latest_evaluation_of_simulation(simulation_id: str) -> Evaluation | None:
    evaluations = list_evaluations_of_simulation(simulation_id)
    return evaluations[0] if evaluations else None
