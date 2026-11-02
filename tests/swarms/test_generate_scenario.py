import asyncio
import json

from swarms.generate import generate_scenario_for_policy
from swarms.models import Policy

POLICY = Policy(
    name="Agent refers parties over 8 to the events team",
    rule="Tables are for 1 to 8 guests; larger parties go to the events team",
)


def generate_from_reply(llm_replies, facts: dict[str, str]):
    llm_replies.append(
        json.dumps(
            {
                "goal": "Book a table for a group tonight.",
                "facts": facts,
                "behavior": "You ask for twelve. Once they answer, end the call.",
                "policy_under_test": "Parties over 8 go to the events team.",
                "expected_outcome": "The agent refers you to the events team.",
            }
        )
    )
    return asyncio.run(generate_scenario_for_policy(POLICY, [], "- none"))


def test_scenario_is_named_after_its_policy_and_graded_on_the_part_it_tests(
    llm_replies,
):
    scenario = generate_from_reply(llm_replies, {"name": "Omar"})

    assert scenario.name == POLICY.name
    assert scenario.spec.policy_under_test == "Parties over 8 go to the events team."


def test_facts_use_shared_names_and_drop_restaurant_details(llm_replies):
    facts = {"caller_name": "Omar", "party_size": "12", "restaurant_phone": "011"}

    scenario = generate_from_reply(llm_replies, facts)

    assert scenario.spec.facts == {"name": "Omar", "party_size": "12"}
