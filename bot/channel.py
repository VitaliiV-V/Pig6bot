import re
import asyncio
from config.config import *
from bot.censor import *
from bot.settings import *
from AI.markovchain import *
from datetime import datetime
from telegram.ext import ContextTypes
from telegram import Update
from bot.protection import *
from economy.pig6economy import *

g = Generator()


last_time = datetime.now()

superlist = []

for code in range(0xE0100, 0xE01F0):
    superlist.append(chr(code))


async def train_background(text):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, g.train, text)


async def reply_in_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_time, messages
    msg = update.channel_post or update.edited_channel_post

    if not msg:
        return

    chat_id = msg.chat_id
    message_id = msg.message_id
    message_text = msg.text or ""

    config = load_config()

    if message_text == "/pig":
        await context.bot.send_message(
            chat_id=chat_id, text=g.gen(6, 10), reply_to_message_id=message_id
        )
    elif message_text == "/svo":
        await context.bot.send_message(
            chat_id=chat_id,
            text="Данная команда поддерживается только в мессенджере МАКС",
            reply_to_message_id=message_id,
        )
    else:
        if msg.via_bot == None:
            asyncio.create_task(train_background(message_text))

    if chat_id != MAIN_CHANNEL_ID:
        await protect_query(context=context, msg=msg, config=config)
        return

    role = await check_signed_user(context=context, msg=msg, config=config)
    ignore = False
    if role == "root":
        await owner_commands(context=context, msg=msg, config=config)
        return
    elif role == "sudo":
        return
    elif role == "user":
        ignore = True

    if await check_super_user(context=context, msg=msg, config=config):
        return

    if await check_owner(context=context, msg=msg, config=config):
        return

    await check_message(context=context, msg=msg, config=config, ignore=ignore)


async def ban_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if not member:
        return

    if (
        member.chat.id == PERSONAL_CHANNEL_ID
        and member.new_chat_member.status == "member"
    ):
        user_id = member.new_chat_member.user.id
        await context.bot.ban_chat_member(chat_id=member.chat.id, user_id=user_id)
