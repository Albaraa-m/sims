import asyncio
import json

import pytest

from swarms.generate import (
    GenerationError,
    describe_agent_tools,
    extract_policies_from_agent_instructions,
)


def extract(instructions: str = "Confirm before booking."):
    return asyncio.run(extract_policies_from_agent_instructions(instructions, "- none"))


def test_policies_are_read_from_the_reply(llm_replies):
    policy = {"name": "Agent confirms before booking", "rule": "Confirm first"}
    llm_replies.append(json.dumps({"policies": [policy]}))

    assert [p.model_dump() for p in extract()] == [policy]


def test_invalid_replies_raise_a_generation_error(llm_replies):
    llm_replies.extend(["not json", json.dumps({"policies": []})])

    with pytest.raises(GenerationError):
        extract()


def test_tools_are_described_by_name_and_docstring():
    assert "create_booking: Create a reservation for today." in describe_agent_tools(
        "v2"
    )
