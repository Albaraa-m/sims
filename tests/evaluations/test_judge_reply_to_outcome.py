import pytest

from evaluations.judge import JudgeReply, grade_judge_reply
from evaluations.models import Outcome


def reply(**changes) -> JudgeReply:
    fields = {
        "situation_happened": True,
        "verdict": "fail",
        "cited_turns": [2],
        "reason": "booked without reading back",
    }
    return JudgeReply.model_validate(fields | changes)


def test_supported_verdict_is_kept():
    assert grade_judge_reply(reply(), turn_count=4).outcome == Outcome.FAIL


@pytest.mark.parametrize(
    "unsupported_reply",
    [
        reply(cited_turns=[7]),
        reply(cited_turns=[]),
        reply(situation_happened=False, verdict="pass"),
        reply(verdict="inconclusive"),
    ],
    ids=["missing turn", "no citations", "situation never came up", "judge unsure"],
)
def test_unsupported_verdict_is_inconclusive(unsupported_reply):
    graded = grade_judge_reply(unsupported_reply, turn_count=4)

    assert graded.outcome == Outcome.INCONCLUSIVE
