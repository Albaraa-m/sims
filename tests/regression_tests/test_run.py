import asyncio

import pytest

from regression_tests import run
from regression_tests.crud import create_test_from_spec, mark_ready
from regression_tests.run import (
    TestNotReadyError,
    build_caller_scenario,
    run_test_against_agent_version,
)
from simulations.crud import create_simulation, list_simulations_of_test


def test_caller_scenario_has_caller_fields_only(spec):
    scenario = build_caller_scenario(spec)
    assert spec.goal in scenario
    assert "party size: 4" in scenario
    assert spec.behavior in scenario
    assert spec.policy_under_test not in scenario
    assert spec.expected_outcome not in scenario


def test_draft_test_is_refused(spec, source_conversation):
    test = create_test_from_spec(source_conversation, spec)
    with pytest.raises(TestNotReadyError):
        asyncio.run(run_test_against_agent_version(test.id, "v1"))


def test_ready_test_starts_one_simulation_per_run(
    spec, source_conversation, monkeypatch
):
    started = []

    async def fake_run_simulation(agent_version, test_id, caller_scenario):
        started.append((agent_version, test_id, caller_scenario))
        return create_simulation(agent_version, test_id)

    monkeypatch.setattr(run, "run_simulation", fake_run_simulation)
    test = mark_ready(create_test_from_spec(source_conversation, spec).id)

    simulations = asyncio.run(run_test_against_agent_version(test.id, "v1", runs=3))

    assert len(simulations) == 3
    assert {(version, test_id) for version, test_id, _ in started} == {("v1", test.id)}
    assert started[0][2] == build_caller_scenario(spec)
    assert len(list_simulations_of_test(test.id)) == 3
