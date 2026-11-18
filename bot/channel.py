import logging
from bot.censor import *
from bot.settings import *
from config.config import *
from telegram import Update
from bot.protection import *
from telegram.ext import ContextTypes, ApplicationHandlerStop
from bot.shadow import check_shadow_post, register_shadow

logger = logging.getLogger(__name__)


async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_in_channel(update, context)
    raise ApplicationHandlerStop


async def reply_in_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Signatures rotate after publication; edits only need content filtering.
    if update.edited_channel_post:
        msg = update.edited_channel_post
        if msg.chat_id == MAIN_CHANNEL_ID:
            await check_edited_content(context, msg, load_config())
        return
    msg = update.channel_post

    if not msg:
        return

    chat_id = msg.chat_id

    config = load_config()

    if chat_id != MAIN_CHANNEL_ID:
        if await register_shadow(context, msg, config):
            return
        await protect_query(context=context, msg=msg, config=config)
        return

    if await check_shadow_post(context, msg, config):
        return

    if await check_owner(context=context, msg=msg, config=config):
        return

    if await check_super_user(context=context, msg=msg, config=config):
        await root_commands(context=context, msg=msg, config=config)
        return

    await check_message(context=context, msg=msg, config=config)
