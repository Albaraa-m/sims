import os

from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
)

from booking.agent import BookingAgent
from booking.store import default_store

load_dotenv()

server = AgentServer()


@server.rtc_session(agent_name="booking-agent")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-3-6-pro", language="en"),
        llm=inference.LLM(model="google/gemma-4-31b-it"),
        tts=inference.TTS(
            model="fishaudio/s2.1-pro", voice="fa4c9eb3dccc4806b382b40d61c6b10a"
        ),
        turn_handling=TurnHandlingOptions(turn_detection=inference.TurnDetector()),
    )
    await session.start(
        agent=BookingAgent(default_store(), os.getenv("AGENT_VERSION", "v2")),
        room=ctx.room,
    )
    await ctx.connect()
    await session.generate_reply(instructions="Greet the user and offer your help.")


if __name__ == "__main__":
    cli.run_app(server)
