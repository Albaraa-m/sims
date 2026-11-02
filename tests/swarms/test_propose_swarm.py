import asyncio
import json

from agents.booking.agent import INSTRUCTIONS_BY_VERSION, RESTAURANT_POLICIES
from core import llm
from swarms.models import Policy
from swarms.propose import find_policies_of_agent_version, propose_swarm


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


def test_v2_prompt_is_the_restaurant_policies():
    # Swarms are generated from RESTAURANT_POLICIES; v2 must stay identical to it.
    assert INSTRUCTIONS_BY_VERSION["v2"] == RESTAURANT_POLICIES


def test_policies_are_found_from_the_restaurant_rules_for_every_version(monkeypatch):
    prompts: list[str] = []

    async def fake_generate_text(prompt: str, _model: str) -> str:
        prompts.append(prompt)
        policy = {"name": "Agent confirms before booking", "rule": "Confirm first"}
        return json.dumps({"policies": [policy]})

    monkeypatch.setattr(llm, "generate_text", fake_generate_text)

    for agent_version in ("v1", "v2"):
        asyncio.run(find_policies_of_agent_version(agent_version))

    v1_prompt, v2_prompt = prompts
    assert v1_prompt == v2_prompt
    assert "Callers hate long calls" not in v1_prompt
