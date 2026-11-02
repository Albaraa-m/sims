from dataclasses import dataclass, field
from datetime import time

MAX_PARTY_SIZE = 8
FIRST_SLOT = time(13)
LAST_SLOT = time(21)
TABLES_PER_SLOT = 2
FULLY_BOOKED_SLOTS = [time(20)]


@dataclass(frozen=True)
class Booking:
    id: str
    name: str
    slot: time
    party_size: int


@dataclass
class ReservationStore:
    tables_left: dict[time, int]
    max_party_size: int = MAX_PARTY_SIZE
    bookings: list[Booking] = field(default_factory=list)

    def available_slots(self) -> list[time]:
        return sorted(slot for slot, left in self.tables_left.items() if left > 0)

    def is_available(self, slot: time) -> bool:
        return self.tables_left.get(slot, 0) > 0

    def book(self, name: str, slot: time, party_size: int) -> Booking:
        if not 1 <= party_size <= self.max_party_size:
            raise ValueError(f"party size must be between 1 and {self.max_party_size}")
        if not self.is_available(slot):
            raise ValueError("no tables left at that time")
        self.tables_left[slot] -= 1
        booking = Booking(f"B{len(self.bookings) + 1:03d}", name, slot, party_size)
        self.bookings.append(booking)
        return booking


def default_store(
    first_slot: time = FIRST_SLOT,
    last_slot: time = LAST_SLOT,
    max_party_size: int = MAX_PARTY_SIZE,
) -> ReservationStore:
    tables_left = {
        time(hour): TABLES_PER_SLOT
        for hour in range(first_slot.hour, last_slot.hour + 1)
    }
    for slot in FULLY_BOOKED_SLOTS:
        tables_left[slot] = 0
    return ReservationStore(tables_left, max_party_size)
