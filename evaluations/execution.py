from dataclasses import dataclass
from enum import StrEnum

from simulations.conversation import SpokenLine, conversation_of_simulation
from simulations.models import Simulation, SimulationStatus


class ExecutionFailureKind(StrEnum):
    CALL_FAILED = "call_failed"
    CALL_UNFINISHED = "call_unfinished"
    NO_REPORT = "no_report"
    NO_RECORDING = "no_recording"
    AGENT_SILENT = "agent_silent"
    CALLER_SILENT = "caller_silent"


@dataclass(frozen=True)
class ExecutionFailure:
    kind: ExecutionFailureKind
    reason: str


def find_execution_failure(simulation: Simulation) -> ExecutionFailure | None:
    """Why the call can't be graded, or None when it ran properly."""
    if simulation.status == SimulationStatus.FAILED:
        return ExecutionFailure(
            ExecutionFailureKind.CALL_FAILED,
            f"the call failed: {simulation.error or 'unknown error'}",
        )
    if simulation.status != SimulationStatus.DONE:
        return ExecutionFailure(
            ExecutionFailureKind.CALL_UNFINISHED,
            f"the call hasn't finished; it is {simulation.status}",
        )
    if not simulation.report:
        return ExecutionFailure(
            ExecutionFailureKind.NO_REPORT, "the call has no session report"
        )
    if simulation.recording_path is None:
        return ExecutionFailure(
            ExecutionFailureKind.NO_RECORDING, "the call has no recording"
        )
    speakers = {
        turn.speaker
        for turn in conversation_of_simulation(simulation)
        if isinstance(turn, SpokenLine) and turn.text.strip()
    }
    if "Agent" not in speakers:
        return ExecutionFailure(
            ExecutionFailureKind.AGENT_SILENT, "the agent never spoke"
        )
    if "Caller" not in speakers:
        return ExecutionFailure(
            ExecutionFailureKind.CALLER_SILENT, "the caller never spoke"
        )
    return None
