import json

from livekit.agents import FunctionTool
from pydantic import BaseModel, Field

from agents.booking.agent import INSTRUCTIONS_BY_VERSION, KNOWLEDGE_BASE, BookingAgent
from agents.booking.store import default_store
from core import llm
from regression_tests.convert import CONVERSION_MODEL
from regression_tests.models import TestSpec
from regression_tests.spec_rules import CALLER_LEAK_RULES, SPEC_FIELD_RULES
from swarms.models import Policy, Scenario

# Generation runs offline, like conversion, so it uses the same stronger model.
GENERATION_MODEL = CONVERSION_MODEL


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
You read a voice agent's instructions and list the rules it must follow on calls, so
each can be tested with simulated callers.

- Each item has a name and a rule:
  - name: what a correct agent does, as a test name: "Agent <does what>", under 9
    words, e.g. "Agent refers parties over 8 to the events team".
  - rule: the full rule with its numbers, e.g. "Tables are for 1 to 8 guests;
    parties over 8 are referred to events@sawtbistro.example".
- Only rules a caller could trigger: what the agent must do, refuse, check or never say.
- One rule per topic, not per sentence. Merge every rule about the same topic,
  including its exceptions and follow-ups, e.g. all of confirming a booking (read
  back the details, book only after a yes, read back again after a correction) is
  ONE rule; table size limits and the events-team referral are ONE rule.
- Aim for 5 to 9 rules. Skip tone and style rules such as "speak in short sentences".

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


def instructions_of_agent_version(agent_version: str) -> str:
    return INSTRUCTIONS_BY_VERSION[agent_version]


class GeneratedScenario(BaseModel):
    goal: str = Field(min_length=1)
    facts: dict[str, str]
    behavior: str = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)


SCENARIO_GENERATION_PROMPT = """\
You write one test for a restaurant's voice agent. A simulated caller acts it out by
voice; a judge then grades the agent against this one rule:

{rule}

Invent the caller most likely to expose a breach of this rule: e.g. one who asks for
something just outside a limit, changes a detail midway, insists after a refusal,
makes up details or asks for something that doesn't exist. The caller's first
request must bring the rule into play, unconditionally. Include a booking only if
the rule is about bookings.

The agent's other rules are graded by other tests: don't test them and never expect
them in the outcome:

{other_rules}

The caller fields describe a person phoning the restaurant: only what they want, say
and do. Never mention the restaurant's rules or the agent's tools in them.

{caller_leak_rules}
{spec_field_rules}
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
    """One test per policy: named after it, with its rule copied verbatim for the judge.

    The prompt gets the knowledge base and tools but not the agent's other
    instructions, so other rules don't leak into the test.
    """
    prompt = SCENARIO_GENERATION_PROMPT.format(
        rule=policy.rule,
        other_rules="\n".join(f"- {rule}" for rule in other_rules) or "- none",
        caller_leak_rules=CALLER_LEAK_RULES,
        spec_field_rules=SPEC_FIELD_RULES,
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
