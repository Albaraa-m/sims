import asyncio
import json
import time

from livekit import api

from agents.dispatch import BOOKING_AGENT, CALLER_AGENT
from core.config import now
from simulations.crud import create_simulation, update_simulation
from simulations.evidence import wait_for_evidence
from simulations.models import Simulation, SimulationStatus

CALL_TIMEOUT_SECONDS = 180
EVIDENCE_WAIT_SECONDS = 20


async def run_simulation(
    agent_version: str,
    test_id: str | None = None,
    caller_scenario: str | None = None,
) -> Simulation:
    simulation = create_simulation(agent_version, test_id)
    try:
        await run_call(simulation, agent_version, caller_scenario)
        evidence = await wait_for_evidence(simulation.id, EVIDENCE_WAIT_SECONDS)
    # Any error must end the simulation as failed, never leave it stuck as running.
    except Exception as error:  # noqa: BLE001
        return update_simulation(
            simulation.id,
            status=SimulationStatus.FAILED,
            error=str(error) or type(error).__name__,
            ended_at=now(),
        )
    return update_simulation(
        simulation.id, status=SimulationStatus.DONE, ended_at=now(), **evidence
    )


async def run_call(
    simulation: Simulation, agent_version: str, caller_scenario: str | None
) -> None:
    room = simulation.room_name
    async with api.LiveKitAPI() as lkapi:
        # LiveKit treats a room with only agents as empty, so empty_timeout must
        # outlast the call; the caller's hang-up or our timeout ends it instead.
        await lkapi.room.create_room(
            api.CreateRoomRequest(name=room, empty_timeout=CALL_TIMEOUT_SECONDS + 30)
        )
        dispatches = [
            # Without a scenario the caller agent falls back to its default caller.
            (CALLER_AGENT, {"scenario": caller_scenario} if caller_scenario else {}),
            (
                BOOKING_AGENT,
                {"simulation_id": simulation.id, "version": agent_version},
            ),
        ]
        for dispatch_name, settings in dispatches:
            await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=dispatch_name, room=room, metadata=json.dumps(settings)
                )
            )
        print(f"started simulation {simulation.id} with booking agent {agent_version}")

        try:
            await wait_for_room_to_close(lkapi, room, CALL_TIMEOUT_SECONDS)
        except TimeoutError:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room))
            raise


async def wait_for_room_to_close(
    lkapi: api.LiveKitAPI, room: str, timeout: float
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rooms = await lkapi.room.list_rooms(api.ListRoomsRequest(names=[room]))
        if not rooms.rooms:
            return
        await asyncio.sleep(2)
    raise TimeoutError(f"timed out after {timeout:.0f}s")
