import bot.tools as tools
import logging
from bot.settings import *
from config.config import *
from bot.protection import *
from bot.moderation import find_profile, reject_blocked, check_flood, current_signature
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


async def check_message(context: ContextTypes.DEFAULT_TYPE, msg, config, ignore=False, profile=None):
    chat_id = msg.chat_id

    message_id = msg.message_id

    message_text = (
        msg.text
        or msg.caption
        or (msg.poll.description if msg.poll else "")
        or (msg.poll.question if msg.poll else "")
        or ""
    )

    profile = profile or find_profile(config, msg)
    if await reject_blocked(context, msg, config, profile):
        return

    # Capture this before check_protection rotates the profile's UUID. Its legacy
    # media grace period is not sufficient evidence for banning an author.
    count_flood = ignore or current_signature(msg, profile)
    try:
        if ignore:
            authorized, trust = True, False
        else:
            authorized, trust = await check_protection(context=context, msg=msg, config=config)
    except (BadRequest, Forbidden, OSError, KeyError, ValueError) as e:
        logger.exception("check_protection failed for chat %s: %s", chat_id, e)
        return

    if not authorized and not ignore:
        await _safe_delete(context, chat_id, message_id, "unverified author")
        return

    if count_flood and await check_flood(context, msg, profile):
        return

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

    if not msg.author_signature and not ignore:
        await _safe_delete(context, chat_id, message_id, "no author signature")
