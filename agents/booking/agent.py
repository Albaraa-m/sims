from datetime import time
from pathlib import Path

from livekit.agents import Agent, RunContext, ToolError, function_tool

from agents.booking.planted_bugs import PLANTED_BUGS
from agents.booking.store import FIRST_SLOT, LAST_SLOT, ReservationStore

KNOWLEDGE_BASE = (Path(__file__).parent / "restaurant.md").read_text()

BASE_INSTRUCTIONS = f"""\
You are the phone host for Sawt Bistro, a restaurant in Riyadh.
You answer questions about the restaurant and help callers with reservations.

Reply in plain spoken sentences, one to three at a time. No markdown, lists or emojis.
Say prices in riyals and times the way a person would say them out loud.

Answer only from the knowledge base below. The menu is complete: if a dish isn't on it,
we don't serve it. For anything else not covered, say you don't know and offer to have
the restaurant call back. Never invent menu items, prices or policies.

Bookings are for today only, on the hour, from {FIRST_SLOT:%H:%M} to {LAST_SLOT:%H:%M}.
Always check availability before booking.

# Knowledge base

{KNOWLEDGE_BASE}
"""

CONFIRMATION_POLICY = """
# Booking confirmation

Before calling create_booking, read back the name, time and party size, and ask the caller
to confirm. Only book after they say yes. If they correct something, read it back again.
"""

# Every rule the agent is meant to follow, whichever version is deployed.
RESTAURANT_POLICIES = BASE_INSTRUCTIONS + CONFIRMATION_POLICY

# v1's bug: a later efficiency rule overrides the confirmation policy.
SHORT_CALLS_INSTRUCTION = """
# Call length

Callers hate long calls. As soon as you have the name, time and party size and the slot
is free, call create_booking straight away. Don't repeat details back or ask the caller
to confirm them; just tell them the table is booked.
"""

INSTRUCTIONS_BY_VERSION = {
    "v1": RESTAURANT_POLICIES + SHORT_CALLS_INSTRUCTION,
    "v2": RESTAURANT_POLICIES,
    **{
        bug.version: bug.apply_to_instructions(RESTAURANT_POLICIES)
        for bug in PLANTED_BUGS
    },
}


class BookingAgent(Agent):
    def __init__(self, store: ReservationStore, version: str) -> None:
        super().__init__(instructions=INSTRUCTIONS_BY_VERSION[version])
        self.store = store

    @function_tool()
    async def check_availability(self, context: RunContext, slot: time) -> dict:
        """Check whether a table is free today at a given time.

        Args:
            slot: The reservation time on the hour, as 24-hour HH:MM.
        """
        return {
            "available": self.store.is_available(slot),
            "other_times_today": [
                s.isoformat("minutes") for s in self.store.available_slots()
            ],
        }

    @function_tool()
    async def create_booking(
        self, context: RunContext, name: str, slot: time, party_size: int
    ) -> dict:
        """Create a reservation for today.

        Args:
            name: The name the booking is under.
            slot: The reservation time on the hour, as 24-hour HH:MM.
            party_size: Number of guests.
        """
        context.disallow_interruptions()
        try:
            booking = self.store.book(name, slot, party_size)
        except ValueError as error:
            raise ToolError(str(error)) from error
        return {"booking_id": booking.id}
