import asyncio
import json
import time

from livekit import api

from agents.dispatch import BOOKING_AGENT, CALLER_AGENT
from simulations.evidence import wait_for_evidence
from simulations.models import Simulation

CALL_TIMEOUT_SECONDS = 180
EVIDENCE_WAIT_SECONDS = 20
# A safety net around the whole attempt: the call timeout only bounds the conversation,
# so anything that hangs after it (polling, evidence) would otherwise run forever.
ATTEMPT_DEADLINE_SECONDS = CALL_TIMEOUT_SECONDS + EVIDENCE_WAIT_SECONDS + 40


class AttemptHungError(Exception):
    pass


async def run_call_attempt(simulation: Simulation, caller_scenario: str | None) -> dict:
    """Places the call for the simulation's current attempt and returns its evidence."""
    deadline = asyncio.timeout(ATTEMPT_DEADLINE_SECONDS)
    try:
        async with deadline:
            await run_call(simulation, caller_scenario)
            return await wait_for_evidence(
                simulation.id, simulation.attempt, EVIDENCE_WAIT_SECONDS
            )
    except TimeoutError as error:
        if not deadline.expired():
            raise  # the call's own timeout, already handled
        await delete_room(simulation.room_name)
        raise AttemptHungError(
            f"attempt hung past {ATTEMPT_DEADLINE_SECONDS}s and was stopped"
        ) from error


async def run_call(simulation: Simulation, caller_scenario: str | None) -> None:
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
                {
                    "simulation_id": simulation.id,
                    "attempt": simulation.attempt,
                    "version": simulation.agent_version,
                },
            ),
        ]
        for dispatch_name, settings in dispatches:
            await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=dispatch_name, room=room, metadata=json.dumps(settings)
                )
            )
        print(
            f"started simulation {simulation.id} attempt {simulation.attempt} "
            f"with booking agent {simulation.agent_version}"
        )

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


async def delete_room(room: str) -> None:
    """Ends a call by closing its room; a room that is already gone is fine."""
    async with api.LiveKitAPI() as lkapi:
        try:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room))
        # The call may close it first, e.g. when a worker ends a cancelled call.
        except api.ServerError as error:
            if error.code != api.ServerErrorCode.NOT_FOUND:
                raise
