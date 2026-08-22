import bot.tools as tools
import logging
from bot.settings import *
from config.config import *
from bot.protection import *
from datetime import datetime
from economy.pig6economy import *
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def check(text):
    try:
        with open("dict.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.exception("Failed to load dict.json: %s", e)
        return False

    text = text.lower()
    text2 = ""
    for i in text:
        val = data.get(i)
        if val is not None:
            if len(text2) == 0 or text2[-1] != val:
                text2 += val

    try:
        config = load_config()
    except (OSError, ValueError) as e:
        logger.exception("Failed to load config in check(): %s", e)
        return False

    for i in config["banned"]:
        if i in text2 or i in text:
            return True

    return False


messages = []


class Message:
    def __init__(self, author_username: str, text: str, message_id: int):
        self.author_username = author_username
        self.text = text
        self.message_id = message_id
        self.created_at = datetime.now()

    def age(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()


async def _safe_delete(context, chat_id, message_id, reason=""):
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except (BadRequest, Forbidden) as e:
        logger.warning(
            "Failed to delete message %s in chat %s (%s): %s",
            message_id,
            chat_id,
            reason,
            e,
        )


async def check_message(context: ContextTypes.DEFAULT_TYPE, msg, config, ignore=False):
    global last_time, messages
    chat_id = msg.chat_id

    message_id = msg.message_id

    message_text = (
        msg.text
        or msg.caption
        or (msg.poll.description if msg.poll else "")
        or (msg.poll.question if msg.poll else "")
        or ""
    )

    bot_name = (await context.bot.get_me()).first_name

    try:
        penis, trust = await check_protection(context=context, msg=msg, config=config)
    except (BadRequest, Forbidden, OSError, KeyError, ValueError) as e:
        logger.exception("check_protection failed for chat %s: %s", chat_id, e)
        return

    if not penis:
        await _safe_delete(context, chat_id, message_id, "banned gif")

    if trust:
        return

    if msg.animation and msg.animation.file_id in config["bad_gifs"]:
        await _safe_delete(context, chat_id, message_id, "banned gif")
        logger.info("Deleted banned gif in chat %s", chat_id)
        return

    if config["ban_messages"] == "all":
        await _safe_delete(context, chat_id, message_id, "ban_messages=all")
        return
    elif config["ban_messages"] == "manual" and check(message_text):
        await _safe_delete(context, chat_id, message_id, "banned content match")
        logger.info("Deleted message with banned content in chat %s", chat_id)
        return

    try:
        if economy.use_code_from_text(message_text):
            return

    except (KeyError, ValueError, OSError) as e:
        logger.exception("economy.use_code_from_text failed in chat %s: %s", chat_id, e)

    if not msg.author_signature:
        await _safe_delete(context, chat_id, message_id, "no author signature")
        return

    if len(messages) >= 10 and messages[-10].age() < 5:
        try:
            await tools.blockall(context=context, msg=None, x=0)
            logger.info("Triggered blockall (flood protection) in chat %s", chat_id)
        except (BadRequest, Forbidden, OSError, ValueError) as e:
            logger.exception("tools.blockall failed for chat %s: %s", chat_id, e)

        for i in range(-min(40, len(messages) - 1), 0):
            if i >= -11 or messages[i].message_text == messages[-1].message_text:
                await _safe_delete(context, chat_id, message_id, "flood cleanup")

    messages.append(Message(msg.author_signature, message_text, message_id))
    if len(messages) > 1000:
        messages.clear()
