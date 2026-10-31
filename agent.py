from pathlib import Path

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

KNOWLEDGE_BASE = (Path(__file__).parent / "restaurant.md").read_text()

INSTRUCTIONS = f"""\
You are the phone host for Sawt Bistro, a restaurant in Riyadh.
You answer questions about the restaurant and help callers with reservations.

Reply in plain spoken sentences, one to three at a time. No markdown, lists or emojis.
Say prices in riyals and times the way a person would say them out loud.

Answer only from the knowledge base below. The menu is complete: if a dish isn't on it,
we don't serve it. For anything else not covered, say you don't know and offer to have
the restaurant call back. Never invent menu items, prices or policies.

# Knowledge base

{KNOWLEDGE_BASE}
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
