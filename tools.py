import time
import secrets
from config import *
from settings import *
from pig6economy import *


def ban(s):
    config = load_config()
    if s not in config["banned_users"]:
        config["banned_users"].append(s)
    save_config(config)


def unban(s):
    config = load_config()
    if s in config["banned_users"]:
        config["banned_users"].remove(s)
    save_config(config)


def setbaseprompt(s):
    config = load_config()
    config["base_prompt"] = s
    save_config(config)


async def blockall(context, msg, x=1):
    bot_name = (await context.bot.get_me()).first_name
    name = str(MAIN_CHANNEL_ID)
    config = load_config()

    config["ban_messages"] = "all"

    save_config(config)

    await context.bot.send_message(
        chat_id=name,
        text=f"⚠️ Уведомление от системы защиты «{bot_name}»:\n"
        "Активирован режим тотальной зачистки.\n"
        "Любая активность будет немедленно удалена.\n"
        "Канал под полным контролем.",
    )
    if x:
        await msg.reply_text(f"Система защиты «{bot_name}» активирована")


superlist = []

for code in range(0xE0100, 0xE01F0):
    superlist.append(chr(code))


def generate_code():
    return "".join(secrets.choice(superlist) for _ in range(5))
