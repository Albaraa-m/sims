from sqlmodel import Session, select

from core import db
from regression_tests.crud import edit_test, promote_test_to_regression_suite
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


def test_editing_a_swarm_test_keeps_it_in_the_swarm(spec):
    swarm = save_swarm_with_tests("s", "v2", ["p"], [Scenario(name="n", spec=spec)])
    with Session(db.engine) as session:
        test = session.exec(select(Test).where(Test.swarm_id == swarm.id)).one()

    edited = edit_test(test.id, goal="Book for five")

    assert edited.swarm_id == swarm.id


def test_editing_a_promoted_test_keeps_it_in_the_regression_suite(spec):
    swarm = save_swarm_with_tests("s", "v2", ["p"], [Scenario(name="n", spec=spec)])
    with Session(db.engine) as session:
        test = session.exec(select(Test).where(Test.swarm_id == swarm.id)).one()
    promote_test_to_regression_suite(test.id)

    edited = edit_test(test.id, goal="Book for five")

    assert (edited.swarm_id, edited.promoted_from_swarm_id) == (None, swarm.id)
