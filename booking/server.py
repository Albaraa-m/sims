import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli

from booking.agent import BookingAgent
from booking.store import default_store
from voice import start_voice_session

load_dotenv()

DISPATCH_NAME = "booking-agent"
VOICE = "fishaudio/s2.1-pro:fa4c9eb3dccc4806b382b40d61c6b10a"
RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"

server = AgentServer()


async def save_recording(ctx: JobContext) -> None:
    recording = ctx.make_session_report().audio_recording_path
    if recording and recording.exists():
        RECORDINGS_DIR.mkdir(exist_ok=True)
        shutil.copy(recording, RECORDINGS_DIR / f"{ctx.room.name}.ogg")


@server.rtc_session(agent_name=DISPATCH_NAME, on_session_end=save_recording)
async def entrypoint(ctx: JobContext):
    settings = json.loads(ctx.job.metadata or "{}")
    version = settings.get("version", os.getenv("AGENT_VERSION", "v2"))
    session = await start_voice_session(
        ctx, BookingAgent(default_store(), version), VOICE, record=True
    )
    await session.generate_reply(instructions="Greet the caller and offer your help.")


if __name__ == "__main__":
    cli.run_app(server)
