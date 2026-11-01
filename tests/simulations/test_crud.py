from simulations.crud import (
    create_test_from_spec,
    edit_test,
    get_source_conversation,
    get_test,
    mark_ready,
    save_transcript_as_source_conversation,
)
from simulations.models import TestSpec, TestStatus

SPEC = TestSpec(
    goal="Book a table for tonight",
    facts={"name": "Dana", "party_size": "4", "time": "19:00"},
    behavior="Friendly and brief. Say yes if asked to confirm.",
    policy_under_test="Confirm details before booking",
    expected_outcome="Agent reads back the details and waits for a yes",
    fixed=["a booking is made"],
    varying=["wording", "details at once or one at a time"],
)


def test_save_transcript_as_source_conversation():
    saved = save_transcript_as_source_conversation(
        "Agent: hi", "booked without confirming", "v1"
    )
    stored = get_source_conversation(saved.id)
    assert (stored.transcript, stored.reported_issue, stored.agent_version) == (
        "Agent: hi",
        "booked without confirming",
        "v1",
    )


def test_create_test_from_spec_starts_as_draft_v1():
    source_conversation = save_transcript_as_source_conversation("Agent: hi")
    test = create_test_from_spec(source_conversation, SPEC)
    assert (test.version, test.status, test.lineage_id) == (
        1,
        TestStatus.DRAFT,
        test.id,
    )
    assert test.spec == test.inferred == SPEC.model_dump()


def test_edit_test_creates_new_version_and_keeps_old():
    original = create_test_from_spec(save_transcript_as_source_conversation("x"), SPEC)
    edited = edit_test(original.id, goal="Book a table for 5")
    assert (edited.version, edited.lineage_id) == (2, original.lineage_id)
    assert edited.spec["goal"] == "Book a table for 5"
    assert edited.inferred == SPEC.model_dump()
    assert get_test(original.id).spec == SPEC.model_dump()


def test_mark_ready():
    test = create_test_from_spec(save_transcript_as_source_conversation("x"), SPEC)
    assert mark_ready(test.id).status == TestStatus.READY
