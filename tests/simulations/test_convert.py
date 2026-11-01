import asyncio
import json

import pytest

from simulations.convert import ConversionError, convert_source_conversation_to_test
from simulations.crud import save_transcript_as_source_conversation

SPEC = {
    "goal": "Book a table for tonight",
    "facts": {"name": "Dana", "party_size": "4", "time": "19:00"},
    "behavior": "Friendly and brief.",
    "policy_under_test": "Confirm details before booking",
    "expected_outcome": "Agent reads back the details and waits for a yes",
    "fixed": ["a booking is made"],
    "varying": ["wording"],
}


def model_replying(*replies):
    remaining = list(replies)

    async def complete_prompt(prompt):
        return remaining.pop(0)

    return complete_prompt


def convert_with_model_replies(*replies):
    source_conversation = save_transcript_as_source_conversation("Agent: hi")
    return asyncio.run(
        convert_source_conversation_to_test(
            source_conversation.id, model_replying(*replies)
        )
    )


def test_failure_found_creates_draft_test():
    outcome = convert_with_model_replies(
        json.dumps({"failure_found": True, "reason": "no confirm", "spec": SPEC})
    )
    assert outcome.test.spec == SPEC


def test_no_failure_creates_no_test():
    outcome = convert_with_model_replies(
        json.dumps({"failure_found": False, "reason": "agent confirmed"})
    )
    assert outcome == (None, "agent confirmed")


def test_invalid_reply_is_retried_once():
    outcome = convert_with_model_replies(
        "not json",
        json.dumps({"failure_found": True, "reason": "x", "spec": SPEC}),
    )
    assert outcome.test is not None


def test_two_invalid_replies_raise():
    with pytest.raises(ConversionError):
        convert_with_model_replies(
            "not json", '{"failure_found": true, "reason": "missing spec"}'
        )
