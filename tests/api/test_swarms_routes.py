import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.routes import swarms as swarms_routes
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
