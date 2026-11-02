import asyncio
import json

from core import llm
from swarms.propose import propose_swarm


def fake_replies(monkeypatch, policies: list[str]) -> None:
    """Answers the policy call with policies and each scenario call with as many as asked."""

    async def fake_generate_text(prompt: str, _model: str) -> str:
        if "list the rules" in prompt:
            return json.dumps({"policies": policies})
        count = int(prompt.split("Write exactly ")[1].split()[0])
        scenario = {
            "name": "n",
            "goal": "g",
            "facts": {},
            "behavior": "b",
            "expected_outcome": "e",
        }
        return json.dumps({"scenarios": [scenario] * count})

    monkeypatch.setattr(llm, "generate_text", fake_generate_text)


def test_proposal_has_exactly_the_requested_tests(monkeypatch):
    fake_replies(monkeypatch, ["A", "B", "C"])

    proposal = asyncio.run(propose_swarm("v2", 7))

    assert [s.spec.policy_under_test for s in proposal.scenarios] == [
        "A",
        "A",
        "A",
        "B",
        "B",
        "C",
        "C",
    ]
    assert proposal.warnings == []


def test_too_few_tests_warns_about_untested_policies(monkeypatch):
    fake_replies(monkeypatch, ["A", "B", "C"])

    proposal = asyncio.run(propose_swarm("v2", 2))

    assert len(proposal.scenarios) == 2
    assert proposal.warnings[0].startswith("1 of 3 policies have no tests")
