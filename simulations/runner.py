import asyncio
import json
import time

from livekit import api

from agents.booking.server import DISPATCH_NAME as BOOKING_AGENT
from agents.caller.server import DISPATCH_NAME as CALLER_AGENT
from config import evidence_dir, now
from simulations.models import (
    Simulation,
    SimulationStatus,
    create_simulation,
    update_simulation,
)

CALL_TIMEOUT_SECONDS = 180
EVIDENCE_WAIT_SECONDS = 20


async def run_simulation(agent_version: str) -> Simulation:
    simulation = create_simulation(agent_version)
    room = simulation.room_name

    async with api.LiveKitAPI() as lkapi:
        # LiveKit treats a room with only agents as empty, so empty_timeout must
        # outlast the call; the caller's hang-up or our timeout ends it instead.
        await lkapi.room.create_room(
            api.CreateRoomRequest(name=room, empty_timeout=CALL_TIMEOUT_SECONDS + 30)
        )
        dispatches = [
            (CALLER_AGENT, {}),
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

        if not await room_closed(lkapi, room, CALL_TIMEOUT_SECONDS):
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room))
            return update_simulation(
                simulation.id,
                status=SimulationStatus.FAILED,
                error=f"timed out after {CALL_TIMEOUT_SECONDS}s",
                ended_at=now(),
            )

    return await store_evidence(simulation.id)


async def room_closed(lkapi: api.LiveKitAPI, room: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rooms = await lkapi.room.list_rooms(api.ListRoomsRequest(names=[room]))
        if not rooms.rooms:
            return True
        await asyncio.sleep(2)
    return False


async def store_evidence(simulation_id: str) -> Simulation:
    directory = evidence_dir(simulation_id)
    report_file = directory / "report.json"
    deadline = time.monotonic() + EVIDENCE_WAIT_SECONDS
    while not report_file.exists() and time.monotonic() < deadline:
        await asyncio.sleep(1)

    if not report_file.exists():
        return update_simulation(
            simulation_id,
            status=SimulationStatus.FAILED,
            error="call ended but the booking agent saved no session report",
            ended_at=now(),
        )
    recording = directory / "audio.ogg"
    return update_simulation(
        simulation_id,
        status=SimulationStatus.DONE,
        report=json.loads(report_file.read_text()),
        recording_path=str(recording) if recording.exists() else None,
        ended_at=now(),
    )
