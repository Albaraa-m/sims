from livekit.agents import Agent
from livekit.agents.beta.tools import EndCallTool

DEFAULT_GOAL = """\
You are Dana, calling Sawt Bistro to book a table for 4 people at 7pm today.
Give the name, time and party size together in your first request.
If the restaurant asks you to confirm the details, confirm them.
"""

INSTRUCTIONS = """\
You are a person phoning a restaurant. You are the caller, not the restaurant.
Speak naturally and briefly, one or two sentences at a time.
Wait for the restaurant to greet you before you speak.
Pursue your goal below. Once the booking is made or clearly impossible, say goodbye
and end the call.

# Your goal

{goal}"""


class CallerAgent(Agent):
    def __init__(self, goal: str = DEFAULT_GOAL) -> None:
        end_call = EndCallTool(
            extra_description="End the call once your goal is done or clearly impossible.",
            delete_room=True,
        )
        super().__init__(
            instructions=INSTRUCTIONS.format(goal=goal), tools=list(end_call.tools)
        )
