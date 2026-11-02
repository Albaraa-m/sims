import asyncio

from pydantic import BaseModel

from swarms.generate import (
    describe_agent_tools,
    extract_policies_from_agent_instructions,
    generate_scenarios_for_policy,
    instructions_of_agent_version,
)
from swarms.models import Scenario
from swarms.split import split_test_count_across_policies


class SwarmProposal(BaseModel):
    agent_version: str
    policies: list[str]
    scenarios: list[Scenario]
    warnings: list[str]


def warnings_for_proposal(
    counts: dict[str, int], scenarios_by_policy: list[list[Scenario]]
) -> list[str]:
    untested = [policy for policy, count in counts.items() if count == 0]
    short = [
        policy
        for (policy, count), scenarios in zip(
            counts.items(), scenarios_by_policy, strict=True
        )
        if 0 < len(scenarios) < count
    ]
    warnings = []
    if untested:
        warnings.append(
            f"{len(untested)} of {len(counts)} policies have no tests. Ask for at least "
            f"{len(counts)} tests to cover every policy."
        )
    if short:
        warnings.append(f"Fewer scenarios than asked for: {'; '.join(short)}")
    return warnings


async def propose_swarm(agent_version: str, test_count: int) -> SwarmProposal:
    """Generates a swarm for the reviewer to edit; nothing is saved."""
    instructions = instructions_of_agent_version(agent_version)
    policies = await extract_policies_from_agent_instructions(
        instructions, describe_agent_tools(agent_version)
    )
    counts = split_test_count_across_policies(test_count, policies)
    scenarios_by_policy = await asyncio.gather(
        *(
            generate_scenarios_for_policy(policy, instructions, count)
            for policy, count in counts.items()
        )
    )
    return SwarmProposal(
        agent_version=agent_version,
        policies=policies,
        scenarios=[s for scenarios in scenarios_by_policy for s in scenarios],
        warnings=warnings_for_proposal(counts, scenarios_by_policy),
    )
