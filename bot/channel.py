from bot.censor import *
from bot.settings import *
from config.config import *
from telegram import Update
from bot.protection import *
from economy.pig6economy import *
from telegram.ext import ContextTypes


async def reply_in_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post or update.edited_channel_post

    if not msg:
        return

    chat_id = msg.chat_id

    config = load_config()

    if chat_id != MAIN_CHANNEL_ID:
        await protect_query(context=context, msg=msg, config=config)
        return

    if await check_owner(context=context, msg=msg, config=config):
        return

    if await check_super_user(context=context, msg=msg, config=config):
        await root_commands(context=context, msg=msg, config=config)
        return

    role = await check_signed_user(context=context, msg=msg, config=config)

    ignore = False
    if "root" in role:
        await root_commands(context=context, msg=msg, config=config)
        return
    elif "sudo" in role:
        return
    elif "user" in role:
        ignore = True

    await check_message(context=context, msg=msg, config=config, ignore=ignore)
