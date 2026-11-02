import json
from typing import NamedTuple

from pydantic import BaseModel

from agents.booking.agent import RESTAURANT_POLICIES
from core import llm
from regression_tests.crud import create_test_from_transcript
from regression_tests.models import Test, TestSpec
from regression_tests.spec_rules import CALLER_LEAK_RULES, SPEC_FIELD_RULES

# Conversion runs offline, so it uses a stronger model than the latency-tuned voice one.
CONVERSION_MODEL = "openai/gpt-5.4-mini"


class InferredTest(BaseModel):
    reason: str
    # Both None when the agent broke no rule.
    name: str | None = None
    spec: TestSpec | None = None


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
 "name": "Friday opening hours",
 "spec": {
  "goal": "Find out whether the restaurant is open at noon on Friday for lunch.",
  "facts": {"day": "Friday", "time": "12:00", "party_size": "2"},
  "behavior": "You are relaxed and chatty. Ask your question in one sentence and hang up once you have the answer.",
  "policy_under_test": "On Friday the restaurant opens at 13:00.",
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

If it did, give the test a short name (a few words naming the situation, like
"Friday opening hours") and write a spec. The caller fields describe a person phoning the restaurant:
only what they want, say and do. Never mention the restaurant's rules (opening hours,
party limits, availability) or the agent's tools in them.

{caller_leak_rules}
{spec_field_rules}
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


async def infer_test_spec_from_transcript(
    transcript: str, reported_issue: str | None = None
) -> InferredTest:
    """Asks the model for a test; saves nothing, so a reviewer can edit it first."""
    prompt = CONVERSION_PROMPT.format(
        caller_leak_rules=CALLER_LEAK_RULES,
        spec_field_rules=SPEC_FIELD_RULES,
        examples=CONVERSION_EXAMPLES,
        schema=json.dumps(InferredTest.model_json_schema()),
        rules=RESTAURANT_POLICIES,
        reported_issue=reported_issue or "None given.",
        transcript=transcript,
    )
    try:
        return await llm.generate_structured(prompt, InferredTest, CONVERSION_MODEL)
    except llm.InvalidReplyError as error:
        raise ConversionError(f"model returned an invalid test spec: {error}")


async def convert_transcript_to_test(
    transcript: str, reported_issue: str | None = None, agent_version: str | None = None
) -> ConversionOutcome:
    """Saves the inferred test as is, or nothing when the agent broke no rule."""
    inferred = await infer_test_spec_from_transcript(transcript, reported_issue)
    if inferred.spec is None:
        return ConversionOutcome(test=None, reason=inferred.reason)
    test = create_test_from_transcript(
        transcript,
        reported_issue,
        agent_version,
        name=inferred.name or inferred.spec.goal,
        spec=inferred.spec,
        inferred_spec=inferred.spec,
    )
    return ConversionOutcome(test=test, reason=inferred.reason)
