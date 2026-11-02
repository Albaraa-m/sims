import json
import os

from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli

from agents.booking.agent import BookingAgent
from agents.booking.planted_bugs import store_for_agent_version
from agents.dispatch import BOOKING_AGENT
from agents.voice import start_voice_session
from simulations.evidence import write_evidence

load_dotenv()

VOICE = "fishaudio/s2.1-pro:fa4c9eb3dccc4806b382b40d61c6b10a"

server = AgentServer()


async def save_evidence(ctx: JobContext) -> None:
    settings = json.loads(ctx.job.metadata or "{}")
    simulation_id = settings.get("simulation_id")
    if not simulation_id:
        return

    report = ctx.make_session_report()
    write_evidence(
        simulation_id,
        settings.get("attempt", 1),
        report.to_dict(),
        report.audio_recording_path,
    )


@server.rtc_session(agent_name=BOOKING_AGENT, on_session_end=save_evidence)
async def entrypoint(ctx: JobContext):
    settings = json.loads(ctx.job.metadata or "{}")
    version = settings.get("version", os.getenv("AGENT_VERSION", "v2"))
    session = await start_voice_session(
        ctx, BookingAgent(store_for_agent_version(version), version), VOICE, record=True
    )
    await session.generate_reply(instructions="Greet the caller and offer your help.")


if __name__ == "__main__":
    cli.run_app(server)
