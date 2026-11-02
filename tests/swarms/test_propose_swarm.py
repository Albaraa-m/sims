import asyncio
import json

from core import llm
from swarms.models import Policy
from swarms.propose import propose_swarm


def test_proposal_has_one_test_per_chosen_policy(monkeypatch):
    async def fake_generate_text(_prompt: str, _model: str) -> str:
        return json.dumps(
            {"goal": "g", "facts": {}, "behavior": "b", "expected_outcome": "e"}
        )

    monkeypatch.setattr(llm, "generate_text", fake_generate_text)
    policies = [
        Policy(name="Agent does A", rule="A"),
        Policy(name="Agent does B", rule="B"),
    ]

    proposal = asyncio.run(propose_swarm("v2", policies))

    assert proposal.policies == ["A", "B"]
    assert [s.name for s in proposal.scenarios] == ["Agent does A", "Agent does B"]
