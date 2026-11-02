import asyncio
import json

from swarms.generate import generate_scenarios_for_policy

POLICY = "Parties over 8 go to the events team"


def scenarios_reply(*names: str) -> str:
    return json.dumps(
        {
            "scenarios": [
                {
                    "name": name,
                    "goal": "Book a table for a group tonight.",
                    "facts": {"name": "Omar", "party_size": "12"},
                    "behavior": "You ask for twelve. Once they answer, end the call.",
                    "expected_outcome": "The agent refers you to the events team.",
                }
                for name in names
            ]
        }
    )


def generate(count: int):
    return asyncio.run(generate_scenarios_for_policy(POLICY, "rules", count))


def test_extra_scenarios_are_dropped(llm_replies):
    llm_replies.append(scenarios_reply("a", "b", "c"))

    assert [s.name for s in generate(2)] == ["a", "b"]


def test_a_short_reply_is_topped_up_once(llm_replies):
    llm_replies.extend([scenarios_reply("a"), scenarios_reply("b", "c")])

    assert [s.name for s in generate(2)] == ["a", "b"]


def test_every_scenario_tests_the_policy_verbatim(llm_replies):
    llm_replies.append(scenarios_reply("a"))

    assert generate(1)[0].spec.policy_under_test == POLICY


def test_no_scenarios_asked_means_no_model_call(llm_replies):
    assert generate(0) == []
