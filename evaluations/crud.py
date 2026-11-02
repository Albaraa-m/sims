from sqlmodel import Session, col, select

from core import db
from evaluations.models import Evaluation
from simulations.models import Simulation, SimulationStatus


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


def current_evaluation_of_simulation(simulation: Simulation) -> Evaluation | None:
    """The grade of the run's latest attempt, once it is done; earlier attempts' grades
    stay in the history but never count."""
    if simulation.status != SimulationStatus.DONE:
        return None
    evaluation = latest_evaluation_of_simulation(simulation.id)
    if evaluation is None or evaluation.attempt != simulation.attempt:
        return None
    return evaluation
