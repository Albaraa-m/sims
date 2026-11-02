import asyncio

import pytest

from simulations import runner
from simulations.models import Simulation


@pytest.fixture
def deleted_rooms(monkeypatch) -> list[str]:
    rooms: list[str] = []

    async def fake_delete_room(room: str) -> None:
        rooms.append(room)

    monkeypatch.setattr(runner, "delete_room", fake_delete_room)
    return rooms


def test_a_hung_attempt_is_stopped_and_its_room_closed(monkeypatch, deleted_rooms):
    async def hang(_simulation, _scenario):
        await asyncio.sleep(10)

    monkeypatch.setattr(runner, "run_call", hang)
    monkeypatch.setattr(runner, "ATTEMPT_DEADLINE_SECONDS", 0.05)
    simulation = Simulation(id="s1", agent_version="v2", attempt=2)

    with pytest.raises(runner.AttemptHungError):
        asyncio.run(runner.run_call_attempt(simulation, None))
    assert deleted_rooms == ["sim-s1-2"]


def test_a_call_timeout_is_reported_as_is(monkeypatch, deleted_rooms):
    async def time_out(_simulation, _scenario):
        raise TimeoutError("timed out after 180s")

    monkeypatch.setattr(runner, "run_call", time_out)

    with pytest.raises(TimeoutError, match="180s"):
        asyncio.run(runner.run_call_attempt(Simulation(agent_version="v2"), None))
    assert deleted_rooms == []
