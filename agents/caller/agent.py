from livekit.agents import Agent
from livekit.agents.beta.tools import EndCallTool

DEFAULT_SCENARIO = """\
You want to book a table for 4 people at 7pm today, under the name Dana.
Give the name, time and party size together in your first request.
If the restaurant reads the details back, confirm them.
Once they tell you the table is booked, thank them and end the call.
"""

INSTRUCTIONS = """\
You are a person phoning a restaurant. You are the caller, not the restaurant.
Speak naturally and briefly, one or two sentences at a time.
Wait for the restaurant to greet you before you speak.
Follow your scenario below. End the call when it says to, or once your goal is done
or clearly impossible.

# Your scenario

{scenario}"""


class CallerAgent(Agent):
    def __init__(self, scenario: str = DEFAULT_SCENARIO) -> None:
        end_call = EndCallTool(
            extra_description="End the call when your scenario says to, or once your goal is done or clearly impossible.",
            delete_room=True,
        )
        super().__init__(
            instructions=INSTRUCTIONS.format(scenario=scenario),
            tools=list(end_call.tools),
        )
