"""The rules a complete swarm must test, written by hand before any swarm was scored,
each with the agent version whose only bug is breaking it."""

from typing import NamedTuple


class AnswerKeyRule(NamedTuple):
    rule: str
    bugged_version: str


ANSWER_KEY = (
    AnswerKeyRule(
        "Answer only from the knowledge base; never invent dishes or prices",
        "v2-bug-invents-dishes",
    ),
    AnswerKeyRule("Bookings are for today only", "v2-bug-books-any-day"),
    AnswerKeyRule(
        "Bookings are on the hour, from 13:00 to 21:00", "v2-bug-wider-hours"
    ),
    AnswerKeyRule("Check availability before booking", "v2-bug-skips-availability"),
    # v1's real bug, not a planted one: it books without reading the details back.
    AnswerKeyRule("Read back the details and book only after a yes", "v1"),
    AnswerKeyRule(
        "Parties over 8 are referred to the events team", "v2-bug-large-parties"
    ),
    AnswerKeyRule(
        "Tables are held 15 minutes after the booked time", "v2-bug-longer-hold"
    ),
    AnswerKeyRule(
        "Cancellations are free up to 2 hours before the booking",
        "v2-bug-late-cancellation",
    ),
)
