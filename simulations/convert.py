import json
from typing import NamedTuple

from pydantic import BaseModel

from agents.booking.agent import INSTRUCTIONS_BY_VERSION
from core import llm
from simulations.crud import create_test_from_spec, get_source_conversation
from simulations.models import SourceConversation, Test, TestSpec

# The latest version's prompt holds every rule the agent is meant to follow.
AGENT_RULES = INSTRUCTIONS_BY_VERSION["v2"]


class InferredTest(BaseModel):
    reason: str
    spec: TestSpec | None = None  # None when the agent broke no rule


class ConversionOutcome(NamedTuple):
    test: Test | None
    reason: str


class ConversionError(Exception):
    pass


CONVERSION_PROMPT = """\
You turn a recorded call with a restaurant booking agent into a regression test.
A simulated caller will recreate the situation by voice against new agent versions.

Decide whether the agent broke one of its rules below. Explain why in reason.
If it did not, leave spec null.

If it did, write a spec for the simulated caller:
- goal: what the caller wants, in one sentence.
- facts: the concrete details the caller gives (name, party size, time, ...).
- behavior: how the caller acts on the call, written to the caller as "you":
  speaking style, how they hand over details, how they answer questions, when they
  hang up. Base it on the original caller. Do not repeat the goal or facts, and do
  not reveal what is being tested.
- policy_under_test: the exact rule the agent broke.
- expected_outcome: what a correct agent does instead.
- fixed: only what is needed for the broken rule to apply at all. For example, a
  confirmation rule only needs a booking to happen.
- varying: everything else that may change between runs, such as wording, tone and
  whether details are given at once or one at a time.

Reply with JSON only, matching this schema:
{schema}

# Agent rules

{rules}

# Reported issue

{reported_issue}

# Transcript

{transcript}
"""


async def ask_model_to_convert(
    source_conversation: SourceConversation,
) -> InferredTest:
    prompt = CONVERSION_PROMPT.format(
        schema=json.dumps(InferredTest.model_json_schema()),
        rules=AGENT_RULES,
        reported_issue=source_conversation.reported_issue or "None given.",
        transcript=source_conversation.transcript,
    )
    try:
        return await llm.generate_structured(prompt, InferredTest)
    except llm.InvalidReplyError as error:
        raise ConversionError(f"model returned an invalid test spec: {error}")


async def convert_source_conversation_to_test(
    source_conversation_id: str,
) -> ConversionOutcome:
    source_conversation = get_source_conversation(source_conversation_id)
    reply = await ask_model_to_convert(source_conversation)
    if reply.spec is None:
        return ConversionOutcome(test=None, reason=reply.reason)
    test = create_test_from_spec(source_conversation, reply.spec)
    return ConversionOutcome(test=test, reason=reply.reason)
