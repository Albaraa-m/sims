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
    async def fake_propose_swarm(agent_version, test_count):
        scenario = Scenario(name="n", spec=spec)
        return SwarmProposal(
            agent_version=agent_version,
            policies=["p"],
            scenarios=[scenario],
            warnings=[],
        )

    monkeypatch.setattr(swarms_routes, "propose_swarm", fake_propose_swarm)

    response = client.post(
        "/api/swarms/generate", json={"agent_version": "v2", "test_count": 1}
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
