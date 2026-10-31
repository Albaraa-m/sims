import json
import os

from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli

from booking.agent import BookingAgent
from booking.store import default_store
from voice import start_voice_session

load_dotenv()

DISPATCH_NAME = "booking-agent"
VOICE = "fishaudio/s2.1-pro:fa4c9eb3dccc4806b382b40d61c6b10a"

server = AgentServer()


@server.rtc_session(agent_name=DISPATCH_NAME)
async def entrypoint(ctx: JobContext):
    settings = json.loads(ctx.job.metadata or "{}")
    version = settings.get("version", os.getenv("AGENT_VERSION", "v2"))
    session = await start_voice_session(
        ctx, BookingAgent(default_store(), version), VOICE
    )
    await session.generate_reply(instructions="Greet the caller and offer your help.")


if __name__ == "__main__":
    cli.run_app(server)
