from simulations.crud import get, save_transcript_as_source_conversation
from simulations.models import SourceConversation


def test_save_transcript_as_source_conversation():
    saved = save_transcript_as_source_conversation(
        "Agent: hi", "booked without confirming", "v1"
    )
    stored = get(SourceConversation, saved.id)
    assert (stored.transcript, stored.reported_issue, stored.agent_version) == (
        "Agent: hi",
        "booked without confirming",
        "v1",
    )
