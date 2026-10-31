import json
import os
import shutil

from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli

from agents.booking.agent import BookingAgent
from agents.booking.store import default_store
from agents.voice import start_voice_session
from config import evidence_dir

load_dotenv()

DISPATCH_NAME = "booking-agent"
VOICE = "fishaudio/s2.1-pro:fa4c9eb3dccc4806b382b40d61c6b10a"

server = AgentServer()


async def save_evidence(ctx: JobContext) -> None:
    simulation_id = json.loads(ctx.job.metadata or "{}").get("simulation_id")
    if not simulation_id:
        return

    report = ctx.make_session_report()
    directory = evidence_dir(simulation_id)
    directory.mkdir(parents=True, exist_ok=True)
    if report.audio_recording_path and report.audio_recording_path.exists():
        shutil.copy(report.audio_recording_path, directory / "audio.ogg")
    # Written last: the runner treats report.json as the signal that evidence is complete.
    (directory / "report.json").write_text(json.dumps(report.to_dict()))


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
