import argparse
import asyncio
import json
import time

from dotenv import load_dotenv
from livekit import api
from sqlmodel import Session

from booking.server import DISPATCH_NAME as BOOKING_AGENT
from caller.server import DISPATCH_NAME as CALLER_AGENT
from db import Simulation, SimulationStatus, engine, now, update_simulation

CALL_TIMEOUT_SECONDS = 180
REPORT_WAIT_SECONDS = 20

load_dotenv()


async def run_simulation(agent_version: str) -> Simulation:
    with Session(engine) as session:
        simulation = Simulation(agent_version=agent_version)
        session.add(simulation)
        session.commit()
        session.refresh(simulation)
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

    if not await report_saved(simulation.id):
        return update_simulation(
            simulation.id,
            status=SimulationStatus.FAILED,
            error="call ended but the booking agent saved no session report",
            ended_at=now(),
        )
    return update_simulation(
        simulation.id, status=SimulationStatus.DONE, ended_at=now()
    )


async def room_closed(lkapi: api.LiveKitAPI, room: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rooms = await lkapi.room.list_rooms(api.ListRoomsRequest(names=[room]))
        if not rooms.rooms:
            return True
        await asyncio.sleep(2)
    return False


async def report_saved(simulation_id: str) -> bool:
    deadline = time.monotonic() + REPORT_WAIT_SECONDS
    while time.monotonic() < deadline:
        with Session(engine) as session:
            if session.get_one(Simulation, simulation_id).report is not None:
                return True
        await asyncio.sleep(1)
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run one simulated call between the caller and the booking agent."
    )
    parser.add_argument("--version", choices=["v1", "v2"], default="v2")
    simulation = asyncio.run(run_simulation(parser.parse_args().version))
    print(f"simulation {simulation.id} {simulation.status}", end="")
    print(f": {simulation.error}" if simulation.error else "")
