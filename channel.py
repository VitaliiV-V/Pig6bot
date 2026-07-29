import uuid
import time
import tools
import secrets
import asyncio
from config import *
from settings import *
from markovchain import *
from datetime import datetime
from telegram.ext import ContextTypes
from telegram import Update, ReplyKeyboardMarkup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from protection import *

g = Generator()


async def train_background(text):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, g.train, text)


last_time = datetime.now()

superlist = []

for code in range(0xE0100, 0xE01F0):
    superlist.append(chr(code))


async def reply_in_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_time, messages
    msg = update.channel_post or update.edited_channel_post

    if not msg:
        return

    chat_id = msg.chat_id
    message_id = msg.message_id
    message_text = msg.text or ""

    bot_name = (await context.bot.get_me()).first_name

    config = load_config()

    if chat_id != MAIN_CHANNEL_ID:
        await protect_query(context=context, msg=msg, config=config)
        return

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

    if await check_super_user(context=context, msg=msg, config=config):
        return

    if await check_owner(context=context, msg=msg, config=config):
        return


async def ban_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    if (
        result.chat.id == PERSONAL_CHANNEL_ID
        and result.new_chat_member.status == "member"
    ):
        user_id = result.new_chat_member.user.id
        await context.bot.ban_chat_member(chat_id=result.chat.id, user_id=user_id)
