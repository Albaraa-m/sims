from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.exc import NoResultFound

from api.schemas import RunDetail, SpokenLine, ToolCall
from regression_tests.crud import get_test
from simulations.crud import get_simulation
from simulations.models import Simulation
from simulations.transcript import SPEAKERS, chat_items, message_text

router = APIRouter(prefix="/api/runs")


def get_simulation_or_404(run_id: str) -> Simulation:
    try:
        return get_simulation(run_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")


def conversation_of_simulation(simulation: Simulation) -> list[SpokenLine | ToolCall]:
    """Spoken lines in order, each tool call paired with its output."""
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


@router.get("/{run_id}")
def read_run(run_id: str) -> RunDetail:
    simulation = get_simulation_or_404(run_id)
    test = get_test(simulation.test_id) if simulation.test_id else None
    return RunDetail(
        id=simulation.id,
        agent_version=simulation.agent_version,
        status=simulation.status,
        started_at=simulation.started_at,
        ended_at=simulation.ended_at,
        error=simulation.error,
        test_id=test and test.id,
        test_name=test and test.name,
        test_version=test and test.version,
        conversation=conversation_of_simulation(simulation),
        has_recording=simulation.recording_path is not None,
    )


@router.get("/{run_id}/recording")
def read_run_recording(run_id: str) -> FileResponse:
    recording_path = get_simulation_or_404(run_id).recording_path
    if recording_path is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} has no recording")
    return FileResponse(recording_path, media_type="audio/ogg")
