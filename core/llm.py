from livekit.agents import inference, llm, utils
from pydantic import BaseModel, ValidationError

from core.config import LLM_MODEL


class InvalidReplyError(Exception):
    pass


async def generate_text(prompt: str, model: str = LLM_MODEL) -> str:
    async with utils.http_context.open():
        chat = llm.ChatContext()
        chat.add_message(role="user", content=prompt)
        reply = ""
        async with inference.LLM(model=model).chat(chat_ctx=chat) as stream:
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    reply += chunk.delta.content
        return reply


def parse_json_reply[Reply: BaseModel](reply: str, schema: type[Reply]) -> Reply:
    json_text = reply.strip().removeprefix("```json").removeprefix("```")
    return schema.model_validate_json(json_text.removesuffix("```").strip())


async def generate_structured[Reply: BaseModel](
    prompt: str, schema: type[Reply]
) -> Reply:
    """Retries once with the validation error, since models often fix their own JSON."""
    reply = await generate_text(prompt)
    try:
        return parse_json_reply(reply, schema)
    except ValidationError as first_error:
        retry_prompt = (
            f"{prompt}\n\nYour previous reply was invalid: {first_error}\n{reply}"
        )
        try:
            return parse_json_reply(await generate_text(retry_prompt), schema)
        except ValidationError as error:
            raise InvalidReplyError(str(error)) from error
