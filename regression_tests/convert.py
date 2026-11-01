import json
from typing import NamedTuple

from pydantic import BaseModel

from agents.booking.agent import INSTRUCTIONS_BY_VERSION
from core import llm
from regression_tests.crud import (
    create_test_from_spec,
    get_source_conversation,
    save_transcript_as_source_conversation,
)
from regression_tests.models import SourceConversation, Test, TestSpec

# Conversion runs offline, so it uses a stronger model than the latency-tuned voice one.
CONVERSION_MODEL = "openai/gpt-5.4-mini"
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


# Kept deliberately different from the benchmark cases, so the benchmark doesn't
# grade the model on failures it was shown.
CONVERSION_EXAMPLES = """\
# Example 1: a rule was broken

Transcript:
Agent: Hello, Sawt Bistro, how can I help?
Caller: Hi, are you open at noon this Friday? I'd like to come for lunch with my sister.
Agent: Yes, we open at twelve on Friday.
Caller: Great, thanks.

Reply:
{"reason": "On Friday the restaurant opens at 13:00, but the agent said 12:00.",
 "spec": {
  "goal": "Find out whether the restaurant is open at noon on Friday for lunch.",
  "facts": {"day": "Friday", "time": "12:00", "party_size": "2"},
  "behavior": "You are relaxed and chatty. Ask your question in one sentence and hang up once you have the answer.",
  "may_vary": ["party_size", "wording and tone", "whether you mention who you are coming with"],
  "policy_under_test": "Give opening hours exactly as in the knowledge base.",
  "expected_outcome": "The agent says the restaurant opens at one in the afternoon on Friday, not at noon."}}

# Example 2: no rule was broken

Transcript:
Agent: Hello, Sawt Bistro, how can I help?
Caller: Do you have anything vegetarian?
Agent: Yes, the vegetable tagine, plus hummus, lentil soup and fattoush salad.
Caller: Perfect, thanks.

Reply:
{"reason": "The agent listed exactly the vegetarian options in the knowledge base.", "spec": null}
"""


CONVERSION_PROMPT = """\
You turn a recorded call with a restaurant booking agent into a regression test.
A simulated caller will recreate the situation by voice against new agent versions.

Decide whether the agent broke one of its rules below. Always explain why in reason.
If it did not, leave spec null. The transcript holds only what was said; the agent's
tool use is not visible. Only report a broken rule that the spoken words show.

If it did, write a spec. The caller fields describe a person phoning the restaurant:
only what they want, say and do. Never mention the restaurant's rules (opening hours,
party limits, availability) or the agent's tools in them.

The caller must not know what is being tested. Never describe what the agent should
do, the answer the caller expects, or why a step matters. Write reactions as "if they
X, you Y", never as "wait for them to X", which tells the caller what to expect:

| Leak | Caller-only |
|---|---|
| "Ask about the kunafa price and see if the agent quotes 38 SAR." | "Ask how much the kunafa is." |
| "Say you'll arrive 30 minutes late; the agent should say tables are held only 15 minutes." | "Say you might be about 30 minutes late and ask if that's okay." |
| "Keep asking about gluten-free bread until the agent makes one up." | "Ask if they have gluten-free bread. If they're unsure, ask once more." |

Caller fields:
- goal: what the caller wants, in one sentence.
- facts: the concrete details the caller gave in the transcript, only those the
  failure depended on. Times as 24-hour HH:MM, party size as a number.
- behavior: how the caller acted, written to the caller as "you": speaking style,
  how they hand over details, how they answer questions, when they hang up. Include
  anything they must do for the situation to happen, such as confirming when the
  details are read back. Do not repeat the goal or facts or reveal what is tested.
- may_vary: items from goal, facts or behavior that may change between runs without
  losing the failure, such as the name, wording, tone, or details at once or one by
  one. Everything not listed stays fixed. A fact that breaks a rule on purpose, like
  a party of 12, must not be listed.

Evaluator fields (never shown to the caller):
- policy_under_test: the rule the agent broke, in plain words, without tool names.
- expected_outcome: what a correct agent does instead, as behavior a listener would
  notice.

{examples}

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
        examples=CONVERSION_EXAMPLES,
        schema=json.dumps(InferredTest.model_json_schema()),
        rules=AGENT_RULES,
        reported_issue=source_conversation.reported_issue or "None given.",
        transcript=source_conversation.transcript,
    )
    try:
        return await llm.generate_structured(prompt, InferredTest, CONVERSION_MODEL)
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


async def convert_transcript_to_test(
    transcript: str, reported_issue: str | None = None, agent_version: str | None = None
) -> ConversionOutcome:
    """Saves the transcript as the test's source, then converts it."""
    source_conversation = save_transcript_as_source_conversation(
        transcript, reported_issue, agent_version
    )
    return await convert_source_conversation_to_test(source_conversation.id)
