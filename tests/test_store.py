from datetime import time

import pytest

from booking.store import FULLY_BOOKED_SLOTS, default_store


def test_booking_takes_a_table():
    store = default_store()
    store.book("Dana", time(19), 4)
    store.book("Omar", time(19), 2)
    assert not store.is_available(time(19))
    assert [b.name for b in store.bookings] == ["Dana", "Omar"]


def test_full_slot_is_rejected():
    store = default_store()
    with pytest.raises(ValueError, match="no tables"):
        store.book("Dana", FULLY_BOOKED_SLOTS[0], 2)
    assert FULLY_BOOKED_SLOTS[0] not in store.available_slots()


@pytest.mark.parametrize("party_size", [0, 9])
def test_party_size_limits(party_size):
    with pytest.raises(ValueError, match="party size"):
        default_store().book("Dana", time(19), party_size)
