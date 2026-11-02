import asyncio
import json

from core import llm
from swarms.propose import PolicyTestCount, propose_swarm


def fake_scenario_replies(monkeypatch, missing_per_reply: int = 0) -> None:
    """Answers each scenario call with as many as asked, minus missing_per_reply."""

    async def fake_generate_text(prompt: str, _model: str) -> str:
        count = int(prompt.split("Write exactly ")[1].split()[0]) - missing_per_reply
        scenario = {
            "name": "n",
            "goal": "g",
            "facts": {},
            "behavior": "b",
            "expected_outcome": "e",
        }
        return json.dumps({"scenarios": [scenario] * count})

    monkeypatch.setattr(llm, "generate_text", fake_generate_text)


def propose(*counts: tuple[str, int]):
    test_counts = [PolicyTestCount(policy=policy, count=n) for policy, n in counts]
    return asyncio.run(propose_swarm("v2", test_counts))


def test_proposal_has_the_chosen_tests_for_each_chosen_policy(monkeypatch):
    fake_scenario_replies(monkeypatch)

    proposal = propose(("A", 2), ("B", 1))

    assert proposal.policies == ["A", "B"]
    assert [s.spec.policy_under_test for s in proposal.scenarios] == ["A", "A", "B"]
    assert proposal.warnings == []


def test_short_replies_are_reported(monkeypatch):
    fake_scenario_replies(monkeypatch, missing_per_reply=1)

    proposal = propose(("A", 2))

    assert len(proposal.scenarios) == 1
    assert "A" in proposal.warnings[0]
