import pytest

from evaluations.execution import ExecutionFailureKind, find_execution_failure
from simulations.models import Simulation, SimulationStatus


def message(role: str, text: str) -> dict:
    return {"type": "message", "role": role, "content": [text]}


def finished_call(*items: dict) -> Simulation:
    return Simulation(
        agent_version="v1",
        status=SimulationStatus.DONE,
        report={"chat_history": {"items": list(items)}},
        recording_path="evidence/x/audio.ogg",
    )


def test_call_where_both_sides_spoke_can_be_graded():
    call = finished_call(message("assistant", "Hello."), message("user", "Hi."))

    assert find_execution_failure(call) is None


@pytest.mark.parametrize(
    "call, kind, reason",
    [
        (
            Simulation(
                agent_version="v1", status=SimulationStatus.FAILED, error="timeout"
            ),
            ExecutionFailureKind.CALL_FAILED,
            "the call failed: timeout",
        ),
        (
            Simulation(agent_version="v1"),
            ExecutionFailureKind.CALL_UNFINISHED,
            "the call hasn't finished; it is queued",
        ),
        (
            Simulation(agent_version="v1", status=SimulationStatus.DONE),
            ExecutionFailureKind.NO_REPORT,
            "the call has no session report",
        ),
        (
            finished_call(message("assistant", "Hello.")),
            ExecutionFailureKind.CALLER_SILENT,
            "the caller never spoke",
        ),
    ],
)
def test_unusable_call_is_an_execution_failure(call, kind, reason):
    failure = find_execution_failure(call)

    assert failure is not None
    assert (failure.kind, failure.reason) == (kind, reason)
