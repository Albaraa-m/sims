from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
)

load_dotenv()

INSTRUCTIONS = """\
You are a friendly voice assistant. Reply in plain spoken sentences, one to three at a time.
No markdown, lists or emojis.
"""

server = AgentServer()


@server.rtc_session(agent_name="booking-agent")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-3-6-pro", language="en"),
        llm=inference.LLM(model="google/gemma-4-31b-it"),
        tts=inference.TTS(model="fishaudio/s2.1-pro", voice="fa4c9eb3dccc4806b382b40d61c6b10a"),
        turn_handling=TurnHandlingOptions(turn_detection=inference.TurnDetector()),
    )
    await session.start(agent=Agent(instructions=INSTRUCTIONS), room=ctx.room)
    await ctx.connect()
    await session.generate_reply(instructions="Greet the user and offer your help.")


if __name__ == "__main__":
    cli.run_app(server)
