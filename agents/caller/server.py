from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli

from agents.caller.agent import CallerAgent
from agents.dispatch import CALLER_AGENT
from agents.voice import start_voice_session

load_dotenv()

VOICE = "cartesia/sonic-3:a167e0f3-df7e-4d52-a9c3-f949145efdab"

server = AgentServer()


@server.rtc_session(agent_name=CALLER_AGENT)
async def entrypoint(ctx: JobContext):
    await start_voice_session(ctx, CallerAgent(), VOICE)


if __name__ == "__main__":
    cli.run_app(server)
