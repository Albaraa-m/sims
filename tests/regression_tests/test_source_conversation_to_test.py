import asyncio
import json

import pytest
from sqlmodel import Session, func, select

from core import db
from regression_tests.convert import (
    ConversionError,
    convert_transcript_to_test,
    infer_test_spec_from_transcript,
)
from regression_tests.crud import get_source_conversation
from regression_tests.models import Test


def get_test_count() -> int:
    with Session(db.engine) as session:
        return session.exec(select(func.count()).select_from(Test)).one()


def convert_to_test(transcript="Agent: Hi"):
    return asyncio.run(convert_transcript_to_test(transcript))


def reply_with_spec(spec) -> str:
    return json.dumps(
        {
            "reason": "booked without confirming",
            "name": "Unconfirmed booking",
            "spec": spec.model_dump(),
        }
    )


def test_reply_with_spec_saves_a_draft_test(llm_replies, spec):
    llm_replies.append(reply_with_spec(spec))

    test = convert_to_test().test

    assert test is not None
    assert test.name == "Unconfirmed booking"
    assert test.spec == test.inferred == spec.model_dump()


def test_reply_without_spec_saves_no_test(llm_replies):
    llm_replies.append(json.dumps({"reason": "agent confirmed"}))

    outcome = convert_to_test()

    assert outcome.test is None
    assert outcome.reason == "agent confirmed"


def test_invalid_reply_is_retried_once(llm_replies, spec):
    llm_replies.extend(["not json", reply_with_spec(spec)])

    assert convert_to_test().test is not None


def test_two_invalid_replies_raise(llm_replies):
    llm_replies.extend(["not json", "still not json"])

    with pytest.raises(ConversionError):
        convert_to_test()


def test_transcript_is_saved_as_the_tests_source(llm_replies, spec):
    llm_replies.append(reply_with_spec(spec))

    outcome = asyncio.run(convert_transcript_to_test("Agent: Hi", "no confirmation"))

    assert outcome.test is not None
    source = get_source_conversation(outcome.test.source_conversation_id)
    assert source.transcript == "Agent: Hi"
    assert source.reported_issue == "no confirmation"


def test_inferring_saves_nothing(llm_replies, spec):
    llm_replies.append(reply_with_spec(spec))

    inferred = asyncio.run(infer_test_spec_from_transcript("Agent: Hi"))

    assert inferred.spec == spec
    assert get_test_count() == 0
