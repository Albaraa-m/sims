import asyncio

from pydantic import BaseModel, Field

from swarms.generate import (
    describe_agent_tools,
    extract_policies_from_agent_instructions,
    generate_scenarios_for_policy,
    instructions_of_agent_version,
)
from swarms.models import Scenario

# Past about 3, scenarios for one policy start repeating each other.
MAX_TESTS_PER_POLICY = 3
MAX_TESTS_PER_SWARM = 40


class PolicyTestCount(BaseModel):
    policy: str
    count: int = Field(ge=1, le=MAX_TESTS_PER_POLICY)


class SwarmProposal(BaseModel):
    agent_version: str
    # Only the policies the reviewer chose; each has at least one test.
    policies: list[str]
    scenarios: list[Scenario]
    warnings: list[str]


async def find_policies_of_agent_version(agent_version: str) -> list[str]:
    return await extract_policies_from_agent_instructions(
        instructions_of_agent_version(agent_version),
        describe_agent_tools(agent_version),
    )


async def propose_swarm(
    agent_version: str, test_counts: list[PolicyTestCount]
) -> SwarmProposal:
    """Writes the chosen number of tests for each chosen policy; nothing is saved."""
    instructions = instructions_of_agent_version(agent_version)
    scenarios_by_policy = await asyncio.gather(
        *(
            generate_scenarios_for_policy(chosen.policy, instructions, chosen.count)
            for chosen in test_counts
        )
    )
    short = [
        chosen.policy
        for chosen, scenarios in zip(test_counts, scenarios_by_policy, strict=True)
        if len(scenarios) < chosen.count
    ]
    return SwarmProposal(
        agent_version=agent_version,
        policies=[chosen.policy for chosen in test_counts],
        scenarios=[s for scenarios in scenarios_by_policy for s in scenarios],
        warnings=[f"Fewer tests than asked for: {'; '.join(short)}"] if short else [],
    )
