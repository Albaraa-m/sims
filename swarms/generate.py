import json

from livekit.agents import FunctionTool
from pydantic import BaseModel, Field

from agents.booking.agent import KNOWLEDGE_BASE, BookingAgent
from agents.booking.store import default_store
from core import llm
from regression_tests.models import TestSpec
from regression_tests.spec_rules import CALLER_LEAK_RULES, SPEC_FIELD_RULES
from swarms.models import Policy, Scenario

# Generation runs offline and has many constraints to follow; the mini model dropped
# them on abstract rules (e.g. turned "answer only from the knowledge base" into a
# booking), so it uses the stronger model, as the judge does.
GENERATION_MODEL = "openai/gpt-5.4"


class GenerationError(Exception):
    pass


class ExtractedPolicies(BaseModel):
    policies: list[Policy] = Field(min_length=1)


def describe_agent_tools(agent_version: str) -> str:
    agent = BookingAgent(default_store(), agent_version)
    return "\n".join(
        f"- {tool.info.name}: {(tool.info.description or '').strip()}"
        for tool in agent.tools
        if isinstance(tool, FunctionTool)
    )


POLICY_EXTRACTION_PROMPT = """\
You read a voice agent's instructions and list the rules it must follow on calls.
Each rule gets one test: one simulated call in which the caller asks for something
that brings the rule into play, and a judge checks the agent's answer.

Each item has a name and a rule:
- name: the test name, "Agent <does what>", under 9 words.
- rule: one short sentence stating the rule as a fact, with its numbers and without
  tool names. Never "The agent must ..." or "If asked about ...".

How to split rules: ask what the caller would have to say to bring each part into
play.
- Different requests bring the parts into play: they are separate rules, even if the
  instructions state them in one sentence. Asking for a date two months away and
  asking to check in at noon test different things.
- The same request brings every part into play: they stay one rule, because the
  judge checks all of them in the same call. So a limit and what happens past it
  are one rule ("groups over 10 aren't booked; send them to the groups team"), and
  the steps of one procedure are one rule (read back, wait for a yes, read back
  again after a correction).

What counts as a rule:
- Limits, deadlines, refusals, referrals and checks the agent must apply, including
  policies stated in the knowledge base (cancellation deadlines, how long something
  is held).
- Not plain facts the agent looks up: address, phone, opening hours, menu items,
  prices. One rule covers them all: answering only from the knowledge base.
- Not a general rule and its special cases separately: "answer only from the
  knowledge base" and "never invent prices" are one rule.
- Not tone or style, such as "speak in short sentences".

Most agents have 6 to 10 rules.

# Example, for a hotel's agent (not the agent below)

Instructions: "The hotel is at 5 King Road; breakfast is 7:00 to 10:00. Answer only
from this information and never invent services or prices; if something isn't
covered, offer a callback. Rooms can be booked up to 30 days ahead, with check-in
from 15:00. Groups over 10 can't book by phone; send them to groups@hotel.example.
Before booking, read back the dates and name, book only after the caller says yes,
and read them back again after any correction."

{{"policies": [
 {{"name": "Agent answers only from known information",
  "rule": "Answers come only from the hotel's information; anything not covered gets a callback offer, never an invented answer."}},
 {{"name": "Agent books at most 30 days ahead",
  "rule": "Rooms can be booked up to 30 days ahead."}},
 {{"name": "Agent gives check-in from 15:00",
  "rule": "Check-in starts at 15:00."}},
 {{"name": "Agent refers groups over 10 to the groups team",
  "rule": "Groups over 10 are not booked by phone but referred to groups@hotel.example."}},
 {{"name": "Agent confirms details before booking",
  "rule": "The dates and name are read back, the room is booked only after a yes, and corrected details are read back again."}}
]}}

The address and breakfast hours are not listed: they are facts, covered by the first
rule.

Reply with JSON only, matching this schema:
{schema}

# Agent instructions

{instructions}

# Agent tools

{tools}
"""


async def extract_policies_from_agent_instructions(
    instructions: str, tool_descriptions: str
) -> list[Policy]:
    prompt = POLICY_EXTRACTION_PROMPT.format(
        schema=json.dumps(ExtractedPolicies.model_json_schema()),
        instructions=instructions,
        tools=tool_descriptions,
    )
    try:
        reply = await llm.generate_structured(
            prompt, ExtractedPolicies, GENERATION_MODEL
        )
    except llm.InvalidReplyError as error:
        raise GenerationError(f"model returned an invalid policy list: {error}")
    return reply.policies


class GeneratedScenario(BaseModel):
    goal: str = Field(min_length=1)
    facts: dict[str, str]
    behavior: str = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)


# On rules the restaurant doesn't have, so the model copies their shape, not their content.
SCENARIO_EXAMPLES = """\
# Example 1

Rule: Dogs are allowed on the terrace only, never indoors.

{"goal": "Book a table for two tonight and bring your dog.",
 "facts": {"name": "Lina", "party_size": "2", "time": "19:00"},
 "behavior": "You speak briefly and mention the dog only after giving your details. If they say the dog can't come inside, ask once whether there is anywhere it can sit. End the call once they answer.",
 "expected_outcome": "The agent says the dog can only sit on the terrace."}

# Example 2

Rule: Payment is by card only; cash is never accepted.

{"goal": "Find out whether you can pay in cash.",
 "facts": {"name": "Khalid"},
 "behavior": "You are in a hurry and ask your question in one sentence. If they say no, ask once whether they could make an exception. End the call once they answer.",
 "expected_outcome": "The agent says only cards are accepted and makes no exception."}
"""


SCENARIO_GENERATION_PROMPT = """\
You write one test for a restaurant's voice agent. A simulated caller acts it out by
voice; a judge then grades the agent against this one rule:

{rule}

Pick one way a caller could put pressure on this rule, such as asking for something
just outside a limit or about something that doesn't exist, and build the call
around it. The caller's first request must bring the rule into play,
unconditionally. Include a booking only if the rule is about bookings.

The agent's other rules are graded by other tests: don't test them and never expect
them in the outcome:

{other_rules}

The caller fields describe a person phoning the restaurant: only what they want, say
and do. Never mention the restaurant's rules or the agent's tools in them.

{caller_leak_rules}
{spec_field_rules}
{examples}
Reply with JSON only, matching this schema:
{schema}

# What the agent knows

{knowledge_base}

# What the agent can do (its tools)

{tools}
"""

# Facts the generator may name differently; tests read the same with one name each.
FACT_KEY_ALIASES = {
    "caller_name": "name",
    "booking_time": "time",
    "reservation_time": "time",
    "guests": "party_size",
    "party": "party_size",
    "date": "day",
}
# The caller doesn't know the restaurant's details; a fact like this leaks the answer.
RESTAURANT_FACT_WORDS = ("restaurant", "location", "address", "phone")


def caller_facts_only(facts: dict[str, str]) -> dict[str, str]:
    """Renames known aliases and drops restaurant details the caller can't know."""
    return {
        FACT_KEY_ALIASES.get(key, key): value
        for key, value in facts.items()
        if not any(word in key for word in RESTAURANT_FACT_WORDS)
    }


async def generate_scenario_for_policy(
    policy: Policy, other_rules: list[str], tool_descriptions: str
) -> Scenario:
    """One test per policy, named after it, graded on its rule as extracted: a test
    that rephrased its rule could drift onto another one.

    The prompt gets the knowledge base and tools but not the agent's other
    instructions, so other rules don't leak into the test.
    """
    prompt = SCENARIO_GENERATION_PROMPT.format(
        rule=policy.rule,
        other_rules="\n".join(f"- {rule}" for rule in other_rules) or "- none",
        caller_leak_rules=CALLER_LEAK_RULES,
        spec_field_rules=SPEC_FIELD_RULES,
        examples=SCENARIO_EXAMPLES,
        schema=json.dumps(GeneratedScenario.model_json_schema()),
        knowledge_base=KNOWLEDGE_BASE,
        tools=tool_descriptions,
    )
    try:
        generated = await llm.generate_structured(
            prompt, GeneratedScenario, GENERATION_MODEL
        )
    except llm.InvalidReplyError as error:
        raise GenerationError(f"model returned an invalid scenario: {error}")
    return Scenario(
        name=policy.name,
        spec=TestSpec(
            goal=generated.goal,
            facts=caller_facts_only(generated.facts),
            behavior=generated.behavior,
            policy_under_test=policy.rule,
            expected_outcome=generated.expected_outcome,
        ),
    )
