import secrets
import asyncio
from config.config import *
from bot.settings import *
from economy.pig6economy import *


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
    name = str(MAIN_CHANNEL_ID)
    config = load_config()

    config["ban_messages"] = "all"

    save_config(config)

    await context.bot.send_message(
        chat_id=name,
        text=(
            "🟠 Активирован режим полной блокировки.\n\n"
            "Все новые сообщения будут автоматически удаляться."
        ),
    )
    if msg:
        await msg.reply_text("🟢 Защита активирована.")


async def disable(context, msg):
    name = str(MAIN_CHANNEL_ID)
    config = load_config()

    config["ban_messages"] = "off"

    save_config(config)

    await context.bot.send_message(
        chat_id=name,
        text=("⚪ Защита отключена."),
    )
    if msg:
        await msg.reply_text("⚪ Защита деактивирована.")


async def EXCOMMUNICADO(context, msg, targetname=""):
    config = load_config()
    config["mode"] = "Judgment Day"
    save_config(config)
    await context.bot.send_message(
        chat_id=MAIN_CHANNEL_ID,
        text=(
            "🔴 Активирован протокол «Judgment Day».\n\n"
            "Защита переведена в максимальный режим.\n"
            "Доступ к каналу ограничен."
            f"\n\nКод подтверждения: {config['Judgment Day Code']}"
        ),
    )

    await asyncio.sleep(1)
    name = targetname
    for i in config["protected_users"]:
        if (msg and i["name"] in msg.reply_to_message.author_signature) or (
            i["name"] in name
        ):
            name = i["name"]
    for i in range(5, 0, -1):
        config = load_config()
        await context.bot.send_message(
            chat_id=MAIN_CHANNEL_ID,
            text=(
                f"{name} EXCOMMUNICADO {i}\n\n"
                f"Код подтверждения: {config['Judgment Day Code']}"
            ),
        )
        await asyncio.sleep(1)
    config = load_config()
    for i in config["protected_users"]:
        if (msg and i["name"] in msg.reply_to_message.author_signature) or (
            i["name"] in targetname
        ):
            i["EXCOMMUNICADO"] = True
            save_config(config)
            await context.bot.send_message(
                i["channel_id"],
                "⚫ Вы объявлены EXCOMMUNICADO\nДоступ к сервисам «Свиньи-6» отныне закрыт для Вас.",
            )
            await context.bot.send_message(
                chat_id=MAIN_CHANNEL_ID,
                text=(
                    f"{name} EXCOMMUNICADO в силе\n\n"
                    "Решением системы безопасности Свинья-6 защита вашего канала отозвана.\n\n"
                    "UUID-подпись аннулирована.\n"
                    "Канал исключён из списка доверенных и внесён в черный список.\n\n"
                    "Вы лишаетесь всех прав и привилегий.\n"
                    "Отныне вы — изгой.\n\n"
                    "Доступ к сервисам Свиньи-6 прекращён.\n\n"
                    "Вердикт окончательный.\n\n"
                    f"Код подтверждения: {config['Judgment Day Code']}"
                ),
            )
    await asyncio.sleep(1)
    config = load_config()
    config["mode"] = "normal"
    save_config(config)
    emoji = "⚪"
    if config["ban_messages"] == "all":
        emoji = "🟠"
    elif config["ban_messages"] == "manual":
        emoji = "🟡"
    await context.bot.send_message(
        chat_id=MAIN_CHANNEL_ID,
        text=(
            f"{emoji} Протокол «Judgment Day» остановлен.\n"
            "Система работает в штатном режиме.\n\n"
            f"Код подтверждения: {config['Judgment Day Code']}"
        ),
    )


async def jday(context, msg):
    name = str(MAIN_CHANNEL_ID)
    config = load_config()
    if config["mode"] == "normal":
        await context.bot.send_message(
            chat_id=name,
            text=(
                "🔴 Активирован протокол «Judgment Day».\n\n"
                "Защита переведена в максимальный режим.\n"
                "Доступ к каналу ограничен."
                f"\n\nКод подтверждения: {config['Judgment Day Code']}"
            ),
        )
        config["mode"] = "Judgment Day"
        if msg:
            await msg.reply_text(f"🔴 Протокол судного дня активирован")

    else:
        emoji = "⚪"
        if config["ban_messages"] == "all":
            emoji = "🟠"
        elif config["ban_messages"] == "manual":
            emoji = "🟡"
        await context.bot.send_message(
            chat_id=name,
            text=(
                f"{emoji} Протокол «Judgment Day» остановлен.\n"
                "Система работает в штатном режиме.\n\n"
                f"Код подтверждения: {config['Judgment Day Code']}"
            ),
        )
        config["mode"] = "normal"
        if msg:
            await msg.reply_text(f"🟢 Протокол судного дня деактивирован")

    save_config(config)


superlist = []

for code in range(0xE0100, 0xE01F0):
    superlist.append(chr(code))


def generate_code():
    return "".join(secrets.choice(superlist) for _ in range(5))
