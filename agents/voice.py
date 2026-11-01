import logging

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    ConversationItemAddedEvent,
    FunctionToolsExecutedEvent,
    JobContext,
    TurnHandlingOptions,
    inference,
    room_io,
)

from config import LLM_MODEL

logger = logging.getLogger("call")

LISTEN_TO_PEOPLE_AND_AGENTS = room_io.RoomOptions(
    participant_kinds=[
        rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD,
        rtc.ParticipantKind.PARTICIPANT_KIND_AGENT,
    ]
)


async def start_voice_session(
    ctx: JobContext, agent: Agent, voice: str, record: bool = False
) -> AgentSession:
    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-3-6-pro", language="en"),
        llm=inference.LLM(model=LLM_MODEL),
        tts=voice,
        turn_handling=TurnHandlingOptions(turn_detection=inference.TurnDetector()),
    )
    log_transcript(session, speaker=type(agent).__name__)
    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=LISTEN_TO_PEOPLE_AND_AGENTS,
        record=record,
    )
    await ctx.connect()
    return session


def log_transcript(session: AgentSession, speaker: str) -> None:
    @session.on("conversation_item_added")
    def on_item(event: ConversationItemAddedEvent) -> None:
        if event.item.type == "message" and event.item.role == "assistant":
            logger.info("%s: %s", speaker, event.item.text_content)

    @session.on("function_tools_executed")
    def on_tools(event: FunctionToolsExecutedEvent) -> None:
        for call, output in event.zipped():
            logger.info(
                "%s tool %s(%s) -> %s",
                speaker,
                call.name,
                call.arguments,
                output.output,
            )
