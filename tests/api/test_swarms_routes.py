import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.routes import swarms as swarms_routes
from simulations import queue
from swarms.models import Scenario
from swarms.propose import SwarmProposal


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def swarm_body(spec) -> dict:
    return {
        "name": "v2 check",
        "agent_version": "v2",
        "policies": [spec.policy_under_test, "Never invent menu items"],
        "scenarios": [{"name": "Says yes at once", "spec": spec.model_dump()}],
    }


def test_generate_returns_a_proposal_and_saves_nothing(client, spec, monkeypatch):
    async def fake_propose_swarm(agent_version, policies):
        scenario = Scenario(name="n", spec=spec)
        return SwarmProposal(
            agent_version=agent_version,
            policies=["p"],
            scenarios=[scenario],
        )

    monkeypatch.setattr(swarms_routes, "propose_swarm", fake_propose_swarm)

    response = client.post(
        "/api/swarms/generate",
        json={
            "agent_version": "v2",
            "policies": [{"name": "Agent does p", "rule": "p"}],
        },
    )

    assert response.json()["scenarios"][0]["name"] == "n"
    assert client.get("/api/swarms").json() == []


def test_saved_swarm_lists_its_policies_and_tests(client, spec):
    swarm_id = client.post("/api/swarms", json=swarm_body(spec)).json()["id"]

    swarm = client.get(f"/api/swarms/{swarm_id}").json()

    assert swarm["policies"] == [spec.policy_under_test, "Never invent menu items"]
    assert [(t["name"], t["status"]) for t in swarm["tests"]] == [
        ("Says yes at once", "ready")
    ]


def test_read_unknown_swarm_is_404(client):
    assert client.get("/api/swarms/missing").status_code == 404


def test_tests_list_hides_swarm_tests_unless_asked(client, spec):
    client.post("/api/swarms", json=swarm_body(spec))

    assert client.get("/api/tests").json() == []
    swarm_tests = client.get("/api/tests", params={"include_swarm_tests": True}).json()
    assert [t["name"] for t in swarm_tests] == ["Says yes at once"]


def test_running_a_swarm_queues_every_test_as_a_numbered_run(client, spec):
    swarm_id = client.post("/api/swarms", json=swarm_body(spec)).json()["id"]

    first = client.post(
        f"/api/swarms/{swarm_id}/runs", json={"agent_versions": ["v1", "v2"]}
    ).json()
    second = client.post(
        f"/api/swarms/{swarm_id}/runs", json={"agent_versions": ["v2"]}
    ).json()

    assert (first["queued"], first["swarm_run_number"]) == (2, 1)
    assert (second["queued"], second["swarm_run_number"]) == (1, 2)
    runs = client.get(
        f"/api/swarms/{swarm_id}/runs", params={"swarm_run_id": first["swarm_run_id"]}
    ).json()
    assert sorted(r["agent_version"] for r in runs) == ["v1", "v2"]


def test_a_swarm_start_over_the_queue_limit_is_refused(client, spec, monkeypatch):
    monkeypatch.setattr(queue, "MAX_QUEUED_RUNS", 1)
    swarm_id = client.post("/api/swarms", json=swarm_body(spec)).json()["id"]

    response = client.post(
        f"/api/swarms/{swarm_id}/runs", json={"agent_versions": ["v1", "v2"]}
    )

    assert response.status_code == 409
    assert client.get(f"/api/swarms/{swarm_id}/runs").json() == []


def test_cancelling_a_run_leaves_the_swarms_other_runs(client, spec):
    swarm_id = client.post("/api/swarms", json=swarm_body(spec)).json()["id"]
    first = client.post(
        f"/api/swarms/{swarm_id}/runs", json={"agent_versions": ["v2"]}
    ).json()
    client.post(f"/api/swarms/{swarm_id}/runs", json={"agent_versions": ["v2"]})

    client.post(f"/api/swarms/{swarm_id}/swarm-runs/{first['swarm_run_id']}/cancel")

    summaries = client.get(f"/api/swarms/{swarm_id}/swarm-runs").json()
    assert [(s["number"], s["status"]) for s in summaries] == [
        (2, "queued"),
        (1, "cancelled"),
    ]


def test_a_promoted_swarm_test_joins_the_regression_suite(client, spec):
    swarm_id = client.post("/api/swarms", json=swarm_body(spec)).json()["id"]
    [test] = client.get(f"/api/swarms/{swarm_id}").json()["tests"]

    promoted = client.post(f"/api/tests/{test['id']}/promote").json()

    assert (promoted["swarm_id"], promoted["promoted_from_swarm_id"]) == (
        None,
        swarm_id,
    )
    assert [t["id"] for t in client.get("/api/tests").json()] == [test["id"]]
    swarm_tests = client.get(f"/api/swarms/{swarm_id}").json()["tests"]
    assert swarm_tests[0]["promoted_from_swarm_id"] == swarm_id
    assert client.post(f"/api/tests/{test['id']}/promote").status_code == 409
