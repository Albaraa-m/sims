from simulations.crud import (
    get_source_conversation,
    save_transcript_as_source_conversation,
)


def test_transcript_is_saved_with_issue_and_agent_version():
    saved = save_transcript_as_source_conversation(
        "Agent: Hi", reported_issue="booked without confirming", agent_version="v1"
    )

    stored = get_source_conversation(saved.id)

    assert stored.transcript == "Agent: Hi"
    assert stored.reported_issue == "booked without confirming"
    assert stored.agent_version == "v1"


def test_issue_and_agent_version_are_optional():
    stored = get_source_conversation(
        save_transcript_as_source_conversation("Agent: Hi").id
    )

    assert stored.reported_issue is None
    assert stored.agent_version is None
