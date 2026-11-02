import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from core.db import save
from evaluations.models import Evaluation, Outcome
from regression_tests.crud import (
    create_test_from_spec,
    list_latest_tests,
    promote_test_to_regression_suite,
)
from simulations.crud import create_simulation, update_simulation
from simulations.models import SimulationStatus
from simulations.queue import RunRequest, admit_runs, claim_next_run, fail_attempt
from swarms.crud import save_swarm_with_tests
from swarms.models import Scenario


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


REPORT = {
    "chat_history": {
        "items": [
            {"type": "message", "role": "assistant", "content": ["Hello."]},
            {
                "type": "function_call",
                "call_id": "c1",
                "name": "create_booking",
                "arguments": '{"party_size": 4}',
            },
            {"type": "function_call_output", "call_id": "c1", "output": "B001"},
            {"type": "message", "role": "user", "content": ["Thanks."]},
        ]
    }
}


def test_read_pairs_tool_calls_with_their_output(client, tmp_path):
    recording = tmp_path / "audio.ogg"
    recording.write_bytes(b"OggS")
    simulation = create_simulation("v1")
    update_simulation(
        simulation.id,
        status=SimulationStatus.DONE,
        report=REPORT,
        recording_path=str(recording),
    )

    run = client.get(f"/api/runs/{simulation.id}").json()

    assert run["conversation"] == [
        {"kind": "speech", "speaker": "Agent", "text": "Hello."},
        {
            "kind": "tool_call",
            "name": "create_booking",
            "arguments": '{"party_size": 4}',
            "output": "B001",
        },
        {"kind": "speech", "speaker": "Caller", "text": "Thanks."},
    ]
    assert run["test_id"] is None
    assert client.get(f"/api/runs/{simulation.id}/recording").content == b"OggS"


def test_run_without_a_recording_is_404(client):
    simulation = create_simulation("v1")

    assert client.get(f"/api/runs/{simulation.id}/recording").status_code == 404


def test_read_unknown_run_is_404(client):
    assert client.get("/api/runs/missing").status_code == 404


def test_read_lists_evaluations_newest_first(client):
    simulation = create_simulation("v1")
    for outcome in (Outcome.FAIL, Outcome.PASS):
        save(Evaluation(simulation_id=simulation.id, outcome=outcome, reason="r"))

    run = client.get(f"/api/runs/{simulation.id}").json()

    assert [e["outcome"] for e in run["evaluations"]] == ["pass", "fail"]


def test_regrade_adds_an_evaluation(client):
    simulation = create_simulation("v1")
    update_simulation(simulation.id, status=SimulationStatus.FAILED, error="timeout")

    evaluation = client.post(f"/api/runs/{simulation.id}/evaluate").json()

    assert evaluation["outcome"] == "execution_failed"
    run = client.get(f"/api/runs/{simulation.id}").json()
    assert len(run["evaluations"]) == 1


def test_regrade_unknown_run_is_404(client):
    assert client.post("/api/runs/missing/evaluate").status_code == 404


def test_list_filters_by_agent_version_and_outcome(client, source_conversation, spec):
    test = create_test_from_spec(source_conversation, "Unconfirmed", spec)
    for agent_version, outcome in [("v1", Outcome.FAIL), ("v2", Outcome.PASS)]:
        simulation = create_simulation(agent_version, test.id)
        update_simulation(simulation.id, status=SimulationStatus.DONE)
        save(Evaluation(simulation_id=simulation.id, outcome=outcome, reason="r"))
    create_simulation("v1")  # an ad-hoc run, outside any test

    def agent_versions_of_runs(**filters) -> list[str]:
        return [
            row["agent_version"]
            for row in client.get("/api/runs", params=filters).json()
        ]

    assert sorted(agent_versions_of_runs()) == ["v1", "v2"]
    assert agent_versions_of_runs(agent_version="v2") == ["v2"]
    assert agent_versions_of_runs(outcome="fail", test_id=test.id) == ["v1"]


def test_list_carries_the_judge_and_the_execution_failure_kind(
    client, source_conversation, spec
):
    test = create_test_from_spec(source_conversation, "Unconfirmed", spec)
    judged = create_simulation("v1", test.id)
    update_simulation(judged.id, status=SimulationStatus.DONE)
    save(
        Evaluation(
            simulation_id=judged.id,
            outcome=Outcome.FAIL,
            reason="booked unconfirmed",
            judge_model="m",
            judge_prompt_version="2",
        )
    )
    broken = create_simulation("v2", test.id)
    update_simulation(broken.id, status=SimulationStatus.FAILED, error="timeout")
    client.post(f"/api/runs/{broken.id}/evaluate")

    rows = {row["id"]: row for row in client.get("/api/runs").json()}

    assert rows[judged.id]["reason"] == "booked unconfirmed"
    assert rows[judged.id]["judge_model"] == "m"
    assert rows[judged.id]["execution_failure_kind"] is None
    assert rows[broken.id]["execution_failure_kind"] == "call_failed"


def test_a_retried_run_shows_its_attempts_and_only_the_last_grade(client):
    [simulation] = admit_runs([RunRequest("v1")])
    claim_next_run("w")
    fail_attempt(simulation.id, 1, "agent didn't join")
    save(Evaluation(simulation_id=simulation.id, outcome=Outcome.PASS, reason="old"))

    run = client.get(f"/api/runs/{simulation.id}").json()

    assert (run["status"], run["attempt"]) == ("queued", 1)
    assert [entry["status"] for entry in run["attempts"]] == ["failed"]


def test_a_run_that_could_not_run_is_listed_as_an_execution_failure(
    client, source_conversation, spec
):
    test = create_test_from_spec(source_conversation, "Unconfirmed", spec)
    broken = create_simulation("v2", test.id)
    update_simulation(broken.id, status=SimulationStatus.FAILED, error="timeout")

    rows = client.get("/api/runs", params={"outcome": "execution_failed"}).json()

    assert [row["id"] for row in rows] == [broken.id]


def test_runs_are_scoped_to_the_regression_suite_or_one_swarm(
    client, source_conversation, spec
):
    regression_test = create_test_from_spec(source_conversation, "Unconfirmed", spec)
    regression_run = create_simulation("v1", regression_test.id)
    swarm = save_swarm_with_tests("s", "v2", ["p"], [Scenario(name="n", spec=spec)])
    [swarm_test] = list_latest_tests(swarm.id)
    [swarm_run] = admit_runs([RunRequest("v2", swarm_test.id)], swarm.id)

    def run_ids(scope: str) -> list[str]:
        return [
            row["id"] for row in client.get("/api/runs", params={"scope": scope}).json()
        ]

    assert run_ids("regression") == [regression_run.id]
    assert run_ids(f"swarm:{swarm.id}") == [swarm_run.id]

    promote_test_to_regression_suite(swarm_test.id)

    assert sorted(run_ids("regression")) == sorted([regression_run.id, swarm_run.id])
