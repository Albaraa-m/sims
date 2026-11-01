import json

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from core import llm
from regression_tests.crud import get_source_conversation, get_test


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def llm_reply(monkeypatch) -> list[str]:
    reply: list[str] = []

    async def fake_generate_text(_prompt: str, _model: str) -> str:
        return reply[0]

    monkeypatch.setattr(llm, "generate_text", fake_generate_text)
    return reply


def test_infer_returns_the_suggested_test(client, llm_reply, spec):
    llm_reply.append(
        json.dumps(
            {"reason": "no read-back", "name": "Unconfirmed", "spec": spec.model_dump()}
        )
    )

    response = client.post("/api/tests/infer", json={"transcript": "Agent: Hi"})

    assert response.json() == {
        "reason": "no read-back",
        "name": "Unconfirmed",
        "spec": spec.model_dump(),
    }


def test_infer_on_a_clean_call_returns_no_spec(client, llm_reply):
    llm_reply.append(json.dumps({"reason": "agent confirmed"}))

    response = client.post("/api/tests/infer", json={"transcript": "Agent: Hi"})

    assert response.json() == {"reason": "agent confirmed", "name": None, "spec": None}


def test_create_saves_the_test_and_its_source(client, spec):
    response = client.post(
        "/api/tests",
        json={
            "transcript": "Agent: Hi",
            "reported_issue": "no read-back",
            "name": "Unconfirmed",
            "spec": spec.model_dump(),
        },
    )

    assert response.status_code == 201
    test = get_test(response.json()["id"])
    assert test.name == "Unconfirmed"
    assert test.inferred is None
    assert (
        get_source_conversation(test.source_conversation_id).transcript == "Agent: Hi"
    )


def test_create_rejects_an_incomplete_spec(client, spec):
    incomplete_spec = spec.model_dump(exclude={"goal"})

    response = client.post(
        "/api/tests",
        json={"transcript": "Agent: Hi", "name": "x", "spec": incomplete_spec},
    )

    assert response.status_code == 422


def test_list_returns_created_tests(client, spec):
    client.post(
        "/api/tests",
        json={
            "transcript": "Agent: Hi",
            "name": "Unconfirmed",
            "spec": spec.model_dump(),
        },
    )

    rows = client.get("/api/tests").json()

    assert [(row["name"], row["version"], row["status"]) for row in rows] == [
        ("Unconfirmed", 1, "draft")
    ]


def test_read_returns_the_spec_and_what_was_inferred(client, spec):
    created = client.post(
        "/api/tests",
        json={
            "transcript": "Agent: Hi",
            "name": "Unconfirmed",
            "spec": {**spec.model_dump(), "goal": "Edited goal"},
            "inferred_spec": spec.model_dump(),
        },
    ).json()

    test = client.get(f"/api/tests/{created['id']}").json()

    assert test["spec"]["goal"] == "Edited goal"
    assert test["inferred"] == spec.model_dump()


def test_read_unknown_test_is_404(client):
    assert client.get("/api/tests/missing").status_code == 404


def test_edit_saves_a_new_draft_version(client, spec):
    created = client.post(
        "/api/tests",
        json={
            "transcript": "Agent: Hi",
            "name": "Unconfirmed",
            "spec": spec.model_dump(),
        },
    ).json()

    edited = client.put(
        f"/api/tests/{created['id']}",
        json={"name": "Renamed", "spec": {**spec.model_dump(), "goal": "New goal"}},
    ).json()

    assert (edited["version"], edited["name"], edited["status"]) == (
        2,
        "Renamed",
        "draft",
    )
    assert edited["spec"]["goal"] == "New goal"
    assert client.get(f"/api/tests/{created['id']}").json()["spec"] == spec.model_dump()
