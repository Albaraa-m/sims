from typing import Literal

from pydantic import BaseModel

from simulations.models import Simulation
from simulations.transcript import SPEAKERS, chat_items, message_text


class SpokenLine(BaseModel):
    kind: Literal["speech"] = "speech"
    speaker: str
    text: str


class ToolCall(BaseModel):
    kind: Literal["tool_call"] = "tool_call"
    name: str
    arguments: str
    output: str | None


def conversation_of_simulation(simulation: Simulation) -> list[SpokenLine | ToolCall]:
    """Spoken lines in order, each tool call paired with its output.

    The list index is the turn number the evaluator cites and the run page shows.
    """
    conversation: list[SpokenLine | ToolCall] = []
    tool_calls_by_id: dict[str, ToolCall] = {}
    for item in chat_items(simulation):
        match item["type"]:
            case "message" if item["role"] in SPEAKERS:
                conversation.append(
                    SpokenLine(speaker=SPEAKERS[item["role"]], text=message_text(item))
                )
            case "function_call":
                tool_call = ToolCall(
                    name=item["name"], arguments=item["arguments"], output=None
                )
                tool_calls_by_id[item["call_id"]] = tool_call
                conversation.append(tool_call)
            case "function_call_output" if item["call_id"] in tool_calls_by_id:
                tool_calls_by_id[item["call_id"]].output = str(item["output"])
    return conversation
