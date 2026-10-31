import argparse
import asyncio
import json
import time
import uuid

from dotenv import load_dotenv
from livekit import api

from booking.server import DISPATCH_NAME as BOOKING_AGENT
from caller.server import DISPATCH_NAME as CALLER_AGENT

CALL_TIMEOUT_SECONDS = 180

load_dotenv()


async def run_call(version: str) -> None:
    room = f"call-{uuid.uuid4().hex[:8]}"
    async with api.LiveKitAPI() as lkapi:
        # LiveKit treats a room with only agents as empty, so empty_timeout must
        # outlast the call; the caller's hang-up or our timeout ends it instead.
        await lkapi.room.create_room(
            api.CreateRoomRequest(name=room, empty_timeout=CALL_TIMEOUT_SECONDS + 30)
        )
        dispatches = [
            (CALLER_AGENT, {}),
            (BOOKING_AGENT, {"version": version}),
        ]
        for dispatch_name, settings in dispatches:
            await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=dispatch_name, room=room, metadata=json.dumps(settings)
                )
            )
        print(f"started {room} with booking agent {version}")

        deadline = time.monotonic() + CALL_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            rooms = await lkapi.room.list_rooms(api.ListRoomsRequest(names=[room]))
            if not rooms.rooms:
                print(f"{room} ended")
                return
            await asyncio.sleep(2)

        await lkapi.room.delete_room(api.DeleteRoomRequest(room=room))
        print(f"{room} timed out after {CALL_TIMEOUT_SECONDS}s and was deleted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run one voice call between the caller and the booking agent."
    )
    parser.add_argument("--version", choices=["v1", "v2"], default="v2")
    asyncio.run(run_call(parser.parse_args().version))
