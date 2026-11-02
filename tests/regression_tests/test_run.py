import pytest

from regression_tests.crud import create_test_from_spec, mark_ready
from regression_tests.run import (
    TestNotReadyError,
    build_caller_scenario,
    queue_test_runs,
)
from simulations.models import SimulationStatus


def test_caller_scenario_has_caller_fields_only(spec):
    scenario = build_caller_scenario(spec)
    assert spec.goal in scenario
    assert "party size: 4" in scenario
    assert spec.behavior in scenario
    assert spec.policy_under_test not in scenario
    assert spec.expected_outcome not in scenario


def test_draft_test_is_refused(spec, source_conversation):
    test = create_test_from_spec(source_conversation, "Unconfirmed booking", spec)
    with pytest.raises(TestNotReadyError):
        queue_test_runs(test.id, ["v1"])


def test_ready_test_queues_its_runs_for_each_version(spec, source_conversation):
    test = mark_ready(
        create_test_from_spec(source_conversation, "Unconfirmed booking", spec).id
    )

    simulations = queue_test_runs(test.id, ["v1", "v2"], runs_per_version=2)

    assert [s.agent_version for s in simulations] == ["v1", "v1", "v2", "v2"]
    assert {s.status for s in simulations} == {SimulationStatus.QUEUED}
