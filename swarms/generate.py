import json

from livekit.agents import FunctionTool
from pydantic import BaseModel, Field

from agents.booking.agent import INSTRUCTIONS_BY_VERSION, BookingAgent
from agents.booking.store import default_store
from core import llm
from regression_tests.convert import CALLER_LEAK_RULES, CONVERSION_MODEL
from regression_tests.models import TestSpec
from swarms.models import Scenario

# Generation runs offline, like conversion, so it uses the same stronger model.
GENERATION_MODEL = CONVERSION_MODEL


class GenerationError(Exception):
    pass


class ExtractedPolicies(BaseModel):
    policies: list[str] = Field(min_length=1)


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

- One rule per item, short and concrete, e.g. "Parties over 8 go to the events team".
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
) -> list[str]:
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
    name: str
    goal: str
    facts: dict[str, str]
    behavior: str
    expected_outcome: str


class GeneratedScenarios(BaseModel):
    scenarios: list[GeneratedScenario]


SCENARIO_GENERATION_PROMPT = """\
You write test scenarios for a voice agent. A simulated caller acts out each one by
voice; a judge then grades the agent against one policy.

Write exactly {count} scenarios that test this policy:

{policy}

Each scenario is a different caller behavior that puts the policy to the test: e.g. a
caller who gives everything at once, one who changes a detail midway, one who
insists after a refusal, one who makes up details or asks for something that doesn't
exist. Make them realistic for this agent, and different from each other{avoid}.

{caller_leak_rules}
Fields:
- name: what the caller does and what the agent should do, as "Caller <does what> →
  agent <does what>", under 12 words, e.g. "Caller says 6, then 11 → agent refers to
  events team". Never the word "test", never tool names.
- goal: what the caller wants, in one sentence, as the caller would say it ("Book a
  table for four tonight"), never what is being checked ("see whether the agent...").
- facts: the concrete details the caller gives. Times as 24-hour HH:MM, party size as
  a number, days relative ("today"). Include a caller name.
- behavior: written to the caller as "you": speaking style, how they hand over
  details, how they react, and when to end the call, tied to something any agent does
  (says the table is booked, answers the question, refuses). Never reveal the policy.
- expected_outcome: what a correct agent does, as behavior a listener would notice.
  Shown only to the judge.

Reply with JSON only, matching this schema:
{schema}

# Agent instructions

{instructions}
"""


async def ask_model_for_scenarios(
    policy: str, instructions: str, count: int, names_to_avoid: list[str]
) -> list[GeneratedScenario]:
    prompt = SCENARIO_GENERATION_PROMPT.format(
        count=count,
        policy=policy,
        avoid=f", and from these: {', '.join(names_to_avoid)}"
        if names_to_avoid
        else "",
        caller_leak_rules=CALLER_LEAK_RULES,
        schema=json.dumps(GeneratedScenarios.model_json_schema()),
        instructions=instructions,
    )
    try:
        reply = await llm.generate_structured(
            prompt, GeneratedScenarios, GENERATION_MODEL
        )
    except llm.InvalidReplyError as error:
        raise GenerationError(f"model returned invalid scenarios: {error}")
    return reply.scenarios


def scenario_testing_policy(generated: GeneratedScenario, policy: str) -> Scenario:
    """The policy is copied verbatim, so the swarm page can group scenarios by it."""
    return Scenario(
        name=generated.name,
        spec=TestSpec(
            goal=generated.goal,
            facts=generated.facts,
            behavior=generated.behavior,
            policy_under_test=policy,
            expected_outcome=generated.expected_outcome,
        ),
    )


async def generate_scenarios_for_policy(
    policy: str, instructions: str, count: int
) -> list[Scenario]:
    """Exactly count scenarios: extras are dropped, a short reply is topped up once."""
    if count == 0:
        return []
    generated = (await ask_model_for_scenarios(policy, instructions, count, []))[:count]
    if len(generated) < count:
        missing = count - len(generated)
        names = [scenario.name for scenario in generated]
        generated += (
            await ask_model_for_scenarios(policy, instructions, missing, names)
        )[:missing]
    return [scenario_testing_policy(scenario, policy) for scenario in generated]
