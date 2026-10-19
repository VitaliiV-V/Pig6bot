import logging
from bot.censor import *
from bot.settings import *
from config.config import *
from telegram import Update
from bot.protection import *
from economy.pig6economy import *
from telegram.ext import ContextTypes, ApplicationHandlerStop
from bot.shadow import check_shadow_post, register_shadow
from bot.moderation import find_profile, profile_from_entry, reject_blocked, check_flood, current_signature

logger = logging.getLogger(__name__)


async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_in_channel(update, context)
    raise ApplicationHandlerStop


async def reply_in_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Signatures rotate after publication; edits must not revalidate old posts.
    if update.edited_channel_post:
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

    profile = find_profile(config, msg)
    if await reject_blocked(context, msg, config, profile):
        return

    if await check_owner(context=context, msg=msg, config=config):
        return

    count_flood = current_signature(msg, profile)
    if await check_super_user(context=context, msg=msg, config=config):
        if count_flood and await check_flood(context, msg, profile):
            return
        await root_commands(context=context, msg=msg, config=config)
        return

    signer = signed_user_id(msg, config)
    role = ""
    if signer:
        entry = config["signed_users"][signer]
        profile = profile_from_entry("signed", entry, signer)
        if await reject_blocked(context, msg, config, profile):
            return
        role = entry.get("role", "")

    ignore = False
    if "root" in role:
        if await check_flood(context, msg, profile):
            return
        await root_commands(context=context, msg=msg, config=config)
        return
    elif "sudo" in role:
        await check_flood(context, msg, profile)
        return
    elif "user" in role:
        ignore = True

    await check_message(context=context, msg=msg, config=config, ignore=ignore, profile=profile)
