import json

from livekit.agents import FunctionTool
from pydantic import BaseModel, Field

from agents.booking.agent import INSTRUCTIONS_BY_VERSION, BookingAgent
from agents.booking.store import default_store
from core import llm
from regression_tests.convert import CONVERSION_MODEL

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
- Merge duplicates; skip tone and style rules such as "speak in short sentences".

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
