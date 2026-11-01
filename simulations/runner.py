import asyncio
import json
import time

from livekit import api

from agents.booking.server import DISPATCH_NAME as BOOKING_AGENT
from agents.caller.server import DISPATCH_NAME as CALLER_AGENT
from config import evidence_dir, now
from simulations.crud import create_simulation, update_simulation
from simulations.models import Simulation, SimulationStatus

CALL_TIMEOUT_SECONDS = 180
EVIDENCE_WAIT_SECONDS = 20


async def run_simulation(agent_version: str) -> Simulation:
    simulation = create_simulation(agent_version)
    try:
        await run_call(simulation, agent_version)
        evidence = await collect_evidence(simulation.id)
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


async def run_call(simulation: Simulation, agent_version: str) -> None:
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


async def collect_evidence(simulation_id: str) -> dict:
    directory = evidence_dir(simulation_id)
    report_file = directory / "report.json"
    deadline = time.monotonic() + EVIDENCE_WAIT_SECONDS
    while not report_file.exists():
        if time.monotonic() > deadline:
            raise TimeoutError(
                "call ended but the booking agent saved no session report"
            )
        await asyncio.sleep(1)

    recording = directory / "audio.ogg"
    return {
        "report": json.loads(report_file.read_text()),
        "recording_path": str(recording) if recording.exists() else None,
    }
