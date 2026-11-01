import json
from collections.abc import Awaitable, Callable
from typing import NamedTuple

from livekit.agents import inference, llm, utils
from pydantic import BaseModel, ValidationError

from agents.booking.agent import INSTRUCTIONS_BY_VERSION
from simulations.crud import create_test_from_spec, get
from simulations.models import SourceConversation, Test, TestSpec

CONVERSION_MODEL = "google/gemma-4-31b-it"
# The latest version's prompt holds every rule the agent is meant to follow.
AGENT_RULES = INSTRUCTIONS_BY_VERSION["v2"]

CompletePrompt = Callable[[str], Awaitable[str]]


class ModelConversionReply(BaseModel):
    failure_found: bool
    reason: str
    spec: TestSpec | None = None


class ConversionOutcome(NamedTuple):
    test: Test | None
    reason: str


class ConversionError(Exception):
    pass


CONVERSION_PROMPT = """\
You turn a recorded call with a restaurant booking agent into a regression test.
A simulated caller will recreate the situation by voice against new agent versions.

Decide whether the agent broke one of its rules below. If it did not, set
failure_found to false, explain why in reason, and leave spec null.

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


async def complete_prompt_with_livekit_inference(prompt: str) -> str:
    async with utils.http_context.open():
        model = inference.LLM(model=CONVERSION_MODEL)
        chat = llm.ChatContext()
        chat.add_message(role="user", content=prompt)
        reply = ""
        async with model.chat(chat_ctx=chat) as stream:
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    reply += chunk.delta.content
        return reply


def parse_model_conversion_reply(reply: str) -> ModelConversionReply:
    json_text = reply.strip().removeprefix("```json").removeprefix("```")
    json_text = json_text.removesuffix("```").strip()
    parsed = ModelConversionReply.model_validate_json(json_text)
    if parsed.failure_found and parsed.spec is None:
        raise ValueError("failure_found is true but spec is missing")
    return parsed


async def ask_model_to_convert(
    source_conversation: SourceConversation, complete_prompt: CompletePrompt
) -> ModelConversionReply:
    prompt = CONVERSION_PROMPT.format(
        schema=json.dumps(ModelConversionReply.model_json_schema()),
        rules=AGENT_RULES,
        reported_issue=source_conversation.reported_issue or "None given.",
        transcript=source_conversation.transcript,
    )
    reply = await complete_prompt(prompt)
    try:
        return parse_model_conversion_reply(reply)
    except (ValidationError, ValueError) as first_error:
        retry_prompt = (
            f"{prompt}\n\nYour previous reply was invalid: {first_error}\n{reply}"
        )
        try:
            return parse_model_conversion_reply(await complete_prompt(retry_prompt))
        except (ValidationError, ValueError) as error:
            raise ConversionError(f"model returned an invalid test spec: {error}")


async def convert_source_conversation_to_test(
    source_conversation_id: str,
    complete_prompt: CompletePrompt = complete_prompt_with_livekit_inference,
) -> ConversionOutcome:
    source_conversation = get(SourceConversation, source_conversation_id)
    reply = await ask_model_to_convert(source_conversation, complete_prompt)
    if not reply.failure_found or reply.spec is None:
        return ConversionOutcome(test=None, reason=reply.reason)
    test = create_test_from_spec(source_conversation, reply.spec)
    return ConversionOutcome(test=test, reason=reply.reason)
