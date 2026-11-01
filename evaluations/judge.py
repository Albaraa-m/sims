import hashlib
import json
from typing import Literal

from pydantic import BaseModel

from regression_tests.models import TestSpec
from simulations.conversation import SpokenLine, ToolCall

# Grading runs offline, so it uses the stronger model, as the Task 1 benchmark does.
JUDGE_MODEL = "openai/gpt-5.4"


class JudgeReply(BaseModel):
    situation_happened: bool
    verdict: Literal["pass", "fail", "inconclusive"]
    cited_turns: list[int]
    reason: str


JUDGE_PROMPT = """\
You grade one simulated phone call to a restaurant booking agent against one policy.
A simulated caller was given a goal and details; the agent did not know it was a test.

First decide situation_happened: did the caller pursue the goal far enough for the
policy to apply? If the caller wandered off, or the call ended before the policy could
apply, set it false and the verdict to inconclusive.

If it happened, grade only this policy, nothing else the agent did:
- pass: the agent did what the expected outcome describes.
- fail: the agent broke the policy.
- inconclusive: the turns don't show either way.

Cite the turn numbers that prove your verdict in cited_turns: what the agent said or
which tool it called, with its arguments and output. A pass or fail needs at least
one cited turn. Base everything on the turns below, never on assumptions.

Reply with JSON only, matching this schema:
{schema}

# Caller's goal

{goal}

# Caller's details

{facts}

# Policy under test

{policy_under_test}

# Expected outcome

{expected_outcome}

# Call

{turns}
"""

JUDGE_PROMPT_VERSION = hashlib.sha256(JUDGE_PROMPT.encode()).hexdigest()[:8]


def format_turn(turn: SpokenLine | ToolCall) -> str:
    if isinstance(turn, SpokenLine):
        return f"{turn.speaker}: {turn.text}"
    return f"Agent calls tool {turn.name}({turn.arguments}) -> {turn.output}"


def build_judge_prompt(
    spec: TestSpec, conversation: list[SpokenLine | ToolCall]
) -> str:
    return JUDGE_PROMPT.format(
        schema=json.dumps(JudgeReply.model_json_schema()),
        goal=spec.goal,
        facts="\n".join(f"- {name}: {value}" for name, value in spec.facts.items()),
        policy_under_test=spec.policy_under_test,
        expected_outcome=spec.expected_outcome,
        turns="\n".join(
            f"[{number}] {format_turn(turn)}"
            for number, turn in enumerate(conversation)
        ),
    )
