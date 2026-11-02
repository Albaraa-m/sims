from sqlmodel import Session, col, select

from core import db
from core.db import get_row
from core.ids import new_id
from regression_tests.models import Test, TestStatus
from swarms.models import Scenario, Swarm


def save_swarm_with_tests(
    name: str, agent_version: str, policies: list[str], scenarios: list[Scenario]
) -> Swarm:
    """Saves the swarm and its tests together, as Ready: the reviewer has confirmed them."""
    swarm = Swarm(name=name, agent_version=agent_version, policies=policies)
    with Session(db.engine) as session:
        session.add(swarm)
        for scenario in scenarios:
            test_id = new_id()
            session.add(
                Test(
                    id=test_id,
                    lineage_id=test_id,
                    name=scenario.name,
                    swarm_id=swarm.id,
                    status=TestStatus.READY,
                    spec=scenario.spec.model_dump(),
                    inferred=scenario.spec.model_dump(),
                )
            )
        session.commit()
        session.refresh(swarm)
        return swarm


def get_swarm(swarm_id: str) -> Swarm:
    return get_row(Swarm, swarm_id)


def list_swarms() -> list[Swarm]:
    with Session(db.engine) as session:
        query = select(Swarm).order_by(col(Swarm.created_at).desc())
        return list(session.exec(query))
