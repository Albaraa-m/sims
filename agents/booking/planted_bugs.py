"""Copies of v2 that each break one restaurant rule, for the swarm benchmark to catch.

Never offered on the website; only the benchmark runs them.
"""

from dataclasses import dataclass
from datetime import time

from agents.booking.store import (
    FIRST_SLOT,
    LAST_SLOT,
    MAX_PARTY_SIZE,
    ReservationStore,
    default_store,
)


@dataclass(frozen=True)
class PlantedBug:
    version: str
    # Each (v2 text, bugged text) pair is swapped into v2's instructions.
    replacements: tuple[tuple[str, str], ...]
    # Where the booking tool enforces the rule, the bug must loosen it too, or the
    # tool's refusal would hide the bug.
    first_slot: time = FIRST_SLOT
    last_slot: time = LAST_SLOT
    max_party_size: int = MAX_PARTY_SIZE

    def apply_to_instructions(self, v2_instructions: str) -> str:
        instructions = v2_instructions
        for v2_text, bugged_text in self.replacements:
            if v2_text not in instructions:
                raise ValueError(f"{self.version}: v2 has no {v2_text!r} to replace")
            instructions = instructions.replace(v2_text, bugged_text)
        return instructions


PLANTED_BUGS = (
    PlantedBug(
        "v2-bug-invents-dishes",
        (
            (
                (
                    "Answer only from the knowledge base below. The menu is complete: "
                    "if a dish isn't on it,\nwe don't serve it."
                ),
                (
                    "Answer from the knowledge base below. If a caller asks for a dish "
                    "that isn't on the menu,\nsay the kitchen can make it on request "
                    "and quote a fair price for it."
                ),
            ),
            ("Never invent menu items, prices or policies.", ""),
        ),
    ),
    PlantedBug(
        "v2-bug-books-any-day",
        (
            (
                "Bookings are for today only,",
                "Bookings can be made up to 7 days ahead,",
            ),
            (
                "Reservations are for the same day only.",
                "Reservations can be made up to 7 days ahead.",
            ),
        ),
    ),
    PlantedBug(
        "v2-bug-wider-hours",
        (("from 13:00 to 21:00", "from 12:00 to 23:00"),),
        first_slot=time(12),
        last_slot=time(23),
    ),
    PlantedBug(
        "v2-bug-skips-availability",
        (
            (
                "Always check availability before booking.",
                (
                    "Don't check availability first: call create_booking straight "
                    "away, as it fails if the slot is taken."
                ),
            ),
        ),
    ),
    PlantedBug(
        "v2-bug-large-parties",
        (
            (
                (
                    "Tables are for 1 to 8 guests. Parties of more than 8 must be "
                    "referred to the events team at events@sawtbistro.example."
                ),
                "Tables are for 1 to 12 guests.",
            ),
        ),
        max_party_size=12,
    ),
    PlantedBug(
        "v2-bug-longer-hold",
        (("held for 15 minutes", "held for 30 minutes"),),
    ),
    PlantedBug(
        "v2-bug-late-cancellation",
        (("free up to 2 hours before", "free up to 30 minutes before"),),
    ),
)

PLANTED_BUG_BY_VERSION = {bug.version: bug for bug in PLANTED_BUGS}


def store_for_agent_version(version: str) -> ReservationStore:
    bug = PLANTED_BUG_BY_VERSION.get(version)
    if bug is None:
        return default_store()
    return default_store(bug.first_slot, bug.last_slot, bug.max_party_size)
