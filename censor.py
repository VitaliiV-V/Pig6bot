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


def check(text):

    with open("dict.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    text = text.lower()
    text2 = ""
    for i in text:
        val = data.get(i)
        if val is not None:
            if len(text2) == 0 or text2[-1] != val:
                text2 += val

    config = load_config()

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


async def check_message(
    context: ContextTypes.DEFAULT_TYPE,
    msg,
    config,
):
    global last_time, messages
    chat_id = msg.chat_id

    message_id = msg.message_id

    message_text = msg.text or ""

    bot_name = (await context.bot.get_me()).first_name

    if msg.animation and msg.animation.file_id in config["bad_gifs"]:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return

    if msg.author_signature in config["banned_users"]:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return

    if config["ban_messages"] == "all":
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return
    elif config["ban_messages"] == "manual" and check(message_text):
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return

    if not msg.author_signature:
        if config["anon_enable"] == 0:
            ok = True
            for i in config["anon_codes"]:
                if i in message_text:
                    ok = False
                    config["anon_codes"] = [
                        code for code in config["anon_codes"] if code != i
                    ]
                    save_config(config)
            if ok:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                return

    if (
        msg.author_signature
        and config["white_lists_mode"] != "off"
        and not (await check_protection(context=context, msg=msg, config=config))
    ):
        ok = False
        if config["white_lists_mode"] == "admins":
            admins = await context.bot.get_chat_administrators(chat_id)
            for u in admins:
                admin = ""
                if u.user.first_name:
                    admin += u.user.first_name
                if u.user.first_name and u.user.last_name:
                    admin += " "
                if u.user.last_name:
                    admin += u.user.last_name

                if admin == msg.author_signature:
                    ok = True

        if (
            config["white_lists_mode"] == "admins"
            or config["white_lists_mode"] == "manual"
        ):
            for u in config["white_list"]:
                if u == msg.author_signature:
                    ok = True

        if not ok:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return

    if len(messages) >= 10 and messages[-10].age() < 5:
        await tools.blockall(context=context, msg=None, x=0)
        for i in range(-min(40, len(messages) - 1), 0):
            if i >= -11 or messages[i].message_text == messages[-1].message_text:
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=messages[i].message_id
                )

    messages.append(Message(msg.author_signature, message_text, message_id))
    if len(messages) > 1000:
        messages.clear()
