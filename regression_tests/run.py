import asyncio

from evaluations.evaluate import evaluate_simulation
from regression_tests.crud import get_test
from regression_tests.models import TestSpec, TestStatus
from simulations.models import Simulation
from simulations.runner import run_simulation


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


async def run_and_evaluate_simulation(
    agent_version: str, test_id: str, caller_scenario: str
) -> Simulation:
    simulation = await run_simulation(agent_version, test_id, caller_scenario)
    await evaluate_simulation(simulation.id)
    return simulation


async def run_test_against_agent_version(
    test_id: str, agent_version: str, runs: int = 1
) -> list[Simulation]:
    test = get_test(test_id)
    if test.status != TestStatus.READY:
        raise TestNotReadyError(f"test {test_id} is {test.status}; mark it ready first")
    caller_scenario = build_caller_scenario(TestSpec.model_validate(test.spec))
    return list(
        await asyncio.gather(
            *(
                run_and_evaluate_simulation(agent_version, test.id, caller_scenario)
                for _ in range(runs)
            )
        )
    )
