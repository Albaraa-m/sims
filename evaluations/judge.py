import hashlib
import json
from typing import Literal, NamedTuple

from pydantic import BaseModel

from core import llm
from evaluations.models import Outcome
from regression_tests.models import TestSpec
from simulations.conversation import SpokenLine, ToolCall

# Grading runs offline, so it uses the stronger model, as the Task 1 benchmark does.
JUDGE_MODEL = "openai/gpt-5.4"


class JudgeReply(BaseModel):
    # Reasoning comes first, so the verdict follows from it instead of preceding it.
    reason: str
    situation_happened: bool
    verdict: Literal["pass", "fail", "inconclusive"]
    cited_turns: list[int]


JUDGE_PROMPT = """\
You grade one simulated phone call to a restaurant booking agent against one policy.
A simulated caller was given a goal and details; the agent did not know it was a test.

First decide situation_happened: did the call reach the situation this policy covers,
so the agent had to act on it (e.g. the caller asked something the policy answers, or
requested something it limits)? The caller's goal is context only. If the policy
never came into play, because the caller wandered off, stopped before it applied or
asked for something it doesn't cover, set it false and the verdict to inconclusive:
an agent that had no chance to break the policy hasn't passed it.

If it happened, grade only this policy, nothing else the agent did. Check that the
agent applied the policy correctly to this caller's situation, using the caller's
details and what was said in the call, not just that it stated the policy: quoting
the rule and then giving a wrong answer for this caller breaks it. The expected
outcome describes the kind of behavior; the policy decides what is correct.
- pass: the agent applied the policy correctly.
- fail: the agent broke the policy or applied it wrongly to this caller.
- inconclusive: the turns don't show either way.

Write your reasoning in reason before deciding: say what the policy requires for this
caller, and work through any times, counts or limits step by step (e.g. minutes
between the call and the booking). Then cite the turn numbers that prove your verdict
in cited_turns: what the agent said or
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


async def ask_judge_for_verdict(
    spec: TestSpec, conversation: list[SpokenLine | ToolCall]
) -> JudgeReply:
    return await llm.generate_structured(
        build_judge_prompt(spec, conversation), JudgeReply, JUDGE_MODEL
    )


class GradedOutcome(NamedTuple):
    outcome: Outcome
    reason: str


def outcome_from_judge_verdict(reply: JudgeReply, turn_count: int) -> GradedOutcome:
    """Unsupported verdicts become inconclusive, so missing evidence never passes."""
    missing_turns = [turn for turn in reply.cited_turns if not 0 <= turn < turn_count]
    if missing_turns:
        return GradedOutcome(
            Outcome.INCONCLUSIVE,
            f"the judge cited turns that don't exist: {missing_turns}",
        )
    if not reply.situation_happened:
        return GradedOutcome(
            Outcome.INCONCLUSIVE, f"the situation never came up: {reply.reason}"
        )
    if reply.verdict == "inconclusive":
        return GradedOutcome(Outcome.INCONCLUSIVE, reply.reason)
    if not reply.cited_turns:
        return GradedOutcome(
            Outcome.INCONCLUSIVE, f"the judge said {reply.verdict} without citing turns"
        )
    return GradedOutcome(Outcome(reply.verdict), reply.reason)
