import asyncio

from pydantic import BaseModel

from swarms.generate import (
    describe_agent_tools,
    extract_policies_from_agent_instructions,
    generate_scenario_for_policy,
    instructions_of_agent_version,
)
from swarms.models import Policy, Scenario


class SwarmProposal(BaseModel):
    agent_version: str
    # The rules of the policies the reviewer chose, one test each.
    policies: list[str]
    scenarios: list[Scenario]


async def find_policies_of_agent_version(agent_version: str) -> list[Policy]:
    return await extract_policies_from_agent_instructions(
        instructions_of_agent_version(agent_version),
        describe_agent_tools(agent_version),
    )


async def propose_swarm(agent_version: str, policies: list[Policy]) -> SwarmProposal:
    """Writes one test per chosen policy; nothing is saved."""
    tool_descriptions = describe_agent_tools(agent_version)
    scenarios = await asyncio.gather(
        *(
            generate_scenario_for_policy(
                policy,
                [other.rule for other in policies if other is not policy],
                tool_descriptions,
            )
            for policy in policies
        )
    )
    return SwarmProposal(
        agent_version=agent_version,
        policies=[policy.rule for policy in policies],
        scenarios=list(scenarios),
    )
