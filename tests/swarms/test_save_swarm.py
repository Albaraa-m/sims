from sqlmodel import Session, select

from core import db
from regression_tests.models import Test, TestStatus
from swarms.crud import get_swarm, save_swarm_with_tests
from swarms.models import Scenario


def test_swarm_is_saved_with_ready_tests(spec):
    swarm = save_swarm_with_tests(
        "v2 check",
        "v2",
        ["Confirm before booking", "Never invent menu items"],
        [Scenario(name="Says yes at once", spec=spec)],
    )

    assert get_swarm(swarm.id).policies == [
        "Confirm before booking",
        "Never invent menu items",
    ]
    with Session(db.engine) as session:
        tests = list(session.exec(select(Test).where(Test.swarm_id == swarm.id)))
    assert [(t.name, t.status, t.source_conversation_id) for t in tests] == [
        ("Says yes at once", TestStatus.READY, None)
    ]
