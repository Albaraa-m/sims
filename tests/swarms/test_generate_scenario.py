import asyncio
import json

from swarms.generate import generate_scenario_for_policy
from swarms.models import Policy

POLICY = Policy(
    name="Agent refers parties over 8 to the events team",
    rule="Tables are for 1 to 8 guests; larger parties go to the events team",
)


def test_scenario_is_named_after_its_policy_and_graded_on_its_rule(llm_replies):
    llm_replies.append(
        json.dumps(
            {
                "goal": "Book a table for a group tonight.",
                "facts": {"name": "Omar", "party_size": "12"},
                "behavior": "You ask for twelve. Once they answer, end the call.",
                "expected_outcome": "The agent refers you to the events team.",
            }
        )
    )

    scenario = asyncio.run(generate_scenario_for_policy(POLICY, "rules"))

    assert scenario.name == POLICY.name
    assert scenario.spec.policy_under_test == POLICY.rule
