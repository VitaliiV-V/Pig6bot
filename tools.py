import time
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


def give_daily_reward():
    config = load_config()
    last_economy_tick = config["last_economy_tick"]
    now = time.time()

    delta = now - last_economy_tick

    days = int(delta // 86400)
    if last_economy_tick == 0:
        days = 1
    if days <= 0:
        return

    economy = Pig6Economy()

    reward = days * 100

    for user_id, _ in economy.get_all_users():
        economy.add_tokens(user_id, reward)

    economy.close()

    config["last_economy_tick"] = time.time()
    save_config(config)
