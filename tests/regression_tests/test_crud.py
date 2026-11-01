import pytest
from pydantic import ValidationError

from regression_tests.crud import (
    create_test_from_spec,
    edit_test,
    get_test,
    list_latest_tests,
    mark_ready,
)
from regression_tests.models import TestStatus


def test_new_test_starts_as_draft_v1(source_conversation, spec):
    test = create_test_from_spec(source_conversation, "Unconfirmed booking", spec)

    assert test.version == 1
    assert test.status == TestStatus.DRAFT
    assert test.spec == spec.model_dump()


def test_hand_written_test_has_no_inferred_spec(source_conversation, spec):
    test = create_test_from_spec(source_conversation, "Unconfirmed booking", spec)

    assert test.inferred is None


def test_editing_adds_a_version_and_keeps_the_original(source_conversation, spec):
    original = create_test_from_spec(
        source_conversation, "Unconfirmed booking", spec, inferred_spec=spec
    )

    edited = edit_test(original.id, goal="Book a table for 5")

    assert edited.version == 2
    assert edited.lineage_id == original.lineage_id
    assert edited.spec["goal"] == "Book a table for 5"
    assert edited.inferred == spec.model_dump()
    assert get_test(original.id).spec == spec.model_dump()


def test_mark_ready(source_conversation, spec):
    test = create_test_from_spec(source_conversation, "Unconfirmed booking", spec)

    assert mark_ready(test.id).status == TestStatus.READY


def test_editing_an_older_version_still_creates_the_latest(source_conversation, spec):
    original = create_test_from_spec(source_conversation, "Unconfirmed booking", spec)
    edit_test(original.id, goal="Book a table for 5")

    edited_again = edit_test(original.id, goal="Book a table for 6")

    assert edited_again.version == 3


def test_editing_an_unknown_field_is_rejected(source_conversation, spec):
    test = create_test_from_spec(source_conversation, "Unconfirmed booking", spec)

    with pytest.raises(ValidationError):
        edit_test(test.id, gaol="typo")


def test_listing_shows_only_the_latest_version_of_each_test(source_conversation, spec):
    first = create_test_from_spec(source_conversation, "First", spec)
    edited_first = edit_test(first.id, goal="Book a table for 5")
    second = create_test_from_spec(source_conversation, "Second", spec)

    listed = list_latest_tests()

    assert [test.id for test in listed] == [second.id, edited_first.id]


def test_editing_can_rename_the_test(source_conversation, spec):
    original = create_test_from_spec(source_conversation, "Unconfirmed booking", spec)

    assert edit_test(original.id, name="No read-back").name == "No read-back"
