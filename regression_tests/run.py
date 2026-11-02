from collections.abc import Sequence

from regression_tests.crud import get_test
from regression_tests.models import TestSpec, TestStatus
from simulations.models import Simulation
from simulations.queue import RunRequest, admit_runs


class TestNotReadyError(Exception):
    pass


def build_caller_scenario(spec: TestSpec) -> str:
    """Only the caller fields: the evaluator fields would let the caller steer the agent."""
    details = "\n".join(
        f"- {name.replace('_', ' ')}: {value}" for name, value in spec.facts.items()
    )
    return (
        f"You want to: {spec.goal}\n\n"
        f"Your details:\n{details}\n\n"
        f"How you act: {spec.behavior}\n\n"
        "Say everything in your own words."
    )


def queue_test_runs(
    test_id: str, agent_versions: Sequence[str], runs_per_version: int = 1
) -> list[Simulation]:
    """Queues the runs for workers to place; raises QueueFullError if they don't fit."""
    test = get_test(test_id)
    if test.status != TestStatus.READY:
        raise TestNotReadyError(f"test {test_id} is {test.status}; mark it ready first")
    requests = [
        RunRequest(agent_version, test.id)
        for agent_version in agent_versions
        for _ in range(runs_per_version)
    ]
    return admit_runs(requests, test.swarm_id)
