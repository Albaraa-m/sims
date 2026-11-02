from sqlmodel import Session, col, select

from core import db
from core.db import get_row, save
from simulations.models import Simulation


def create_simulation(agent_version: str, test_id: str | None = None) -> Simulation:
    """A call record outside the queue, e.g. for tests and benchmarks."""
    return save(Simulation(agent_version=agent_version, test_id=test_id, attempt=1))


def get_simulation(simulation_id: str) -> Simulation:
    return get_row(Simulation, simulation_id)


def update_simulation(simulation_id: str, **changes) -> Simulation:
    simulation = get_row(Simulation, simulation_id)
    for field, value in changes.items():
        setattr(simulation, field, value)
    return save(simulation)


def list_simulations_of_test(test_id: str) -> list[Simulation]:
    with Session(db.engine) as session:
        query = (
            select(Simulation)
            .where(Simulation.test_id == test_id)
            .order_by(col(Simulation.agent_version), col(Simulation.started_at))
        )
        return list(session.exec(query).all())
