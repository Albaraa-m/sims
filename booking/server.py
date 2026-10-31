import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli

from booking.agent import BookingAgent
from booking.store import default_store
from db import update_simulation
from voice import start_voice_session

load_dotenv()

DISPATCH_NAME = "booking-agent"
VOICE = "fishaudio/s2.1-pro:fa4c9eb3dccc4806b382b40d61c6b10a"
RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"

server = AgentServer()


async def save_evidence(ctx: JobContext) -> None:
    simulation_id = json.loads(ctx.job.metadata or "{}").get("simulation_id")
    if not simulation_id:
        return

    report = ctx.make_session_report()
    recording_path = None
    if report.audio_recording_path and report.audio_recording_path.exists():
        RECORDINGS_DIR.mkdir(exist_ok=True)
        recording_path = RECORDINGS_DIR / f"{simulation_id}.ogg"
        shutil.copy(report.audio_recording_path, recording_path)

    update_simulation(
        simulation_id,
        report=report.to_dict(),
        recording_path=str(recording_path) if recording_path else None,
    )


@server.rtc_session(agent_name=DISPATCH_NAME, on_session_end=save_evidence)
async def entrypoint(ctx: JobContext):
    settings = json.loads(ctx.job.metadata or "{}")
    version = settings.get("version", os.getenv("AGENT_VERSION", "v2"))
    session = await start_voice_session(
        ctx, BookingAgent(default_store(), version), VOICE, record=True
    )
    await session.generate_reply(instructions="Greet the caller and offer your help.")


if __name__ == "__main__":
    cli.run_app(server)
