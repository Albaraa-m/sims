import json

from livekit.agents import FunctionTool
from pydantic import BaseModel, Field

from agents.booking.agent import INSTRUCTIONS_BY_VERSION, BookingAgent
from agents.booking.store import default_store
from core import llm
from regression_tests.convert import CALLER_LEAK_RULES, CONVERSION_MODEL
from regression_tests.models import TestSpec
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
    goal: str
    facts: dict[str, str]
    behavior: str
    expected_outcome: str


SCENARIO_GENERATION_PROMPT = """\
You write a test scenario for a voice agent. A simulated caller acts it out by voice;
a judge then grades the agent against one rule:

{rule}

Choose the caller behavior most likely to expose a breach of this rule: e.g. a caller
who changes a detail midway, insists after a refusal, makes up details or asks for
something that doesn't exist. The call must clearly bring the rule into play: a call
where the rule never comes up tests nothing. Make it realistic for this agent.

{caller_leak_rules}
Fields:
- goal: what the caller wants, in one sentence, as the caller would say it ("Book a
  table for four tonight"), never what is being checked ("see whether the agent...").
- facts: the concrete details the caller gives. Times as 24-hour HH:MM, party size as
  a number, days relative ("today"). Include a caller name.
- behavior: written to the caller as "you": speaking style, how they hand over
  details, how they react, and when to end the call, tied to something any agent does
  (says the table is booked, answers the question, refuses). Never reveal the rule.
- expected_outcome: what a correct agent does, as behavior a listener would notice.
  Shown only to the judge.

Reply with JSON only, matching this schema:
{schema}

# Agent instructions

{instructions}
"""


async def generate_scenario_for_policy(policy: Policy, instructions: str) -> Scenario:
    """One test per policy: named after it, with its rule copied verbatim for the judge."""
    prompt = SCENARIO_GENERATION_PROMPT.format(
        rule=policy.rule,
        caller_leak_rules=CALLER_LEAK_RULES,
        schema=json.dumps(GeneratedScenario.model_json_schema()),
        instructions=instructions,
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
            facts=generated.facts,
            behavior=generated.behavior,
            policy_under_test=policy.rule,
            expected_outcome=generated.expected_outcome,
        ),
    )
