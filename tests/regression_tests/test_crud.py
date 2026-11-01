from regression_tests.crud import create_test_from_spec, edit_test, get_test, mark_ready
from regression_tests.models import TestStatus


def test_new_test_starts_as_draft_v1(source_conversation, spec):
    test = create_test_from_spec(source_conversation, spec)

    assert test.version == 1
    assert test.status == TestStatus.DRAFT
    assert test.spec == test.inferred == spec.model_dump()


def test_editing_adds_a_version_and_keeps_the_original(source_conversation, spec):
    original = create_test_from_spec(source_conversation, spec)

    edited = edit_test(original.id, goal="Book a table for 5")

    assert edited.version == 2
    assert edited.lineage_id == original.lineage_id
    assert edited.spec["goal"] == "Book a table for 5"
    assert edited.inferred == spec.model_dump()
    assert get_test(original.id).spec == spec.model_dump()


def test_mark_ready(source_conversation, spec):
    test = create_test_from_spec(source_conversation, spec)

    assert mark_ready(test.id).status == TestStatus.READY


def test_editing_an_older_version_still_creates_the_latest(source_conversation, spec):
    original = create_test_from_spec(source_conversation, spec)
    edit_test(original.id, goal="Book a table for 5")

    edited_again = edit_test(original.id, goal="Book a table for 6")

    assert edited_again.version == 3

