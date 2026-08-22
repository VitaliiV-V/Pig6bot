import secrets
import asyncio
import logging
from config.config import *
from bot.settings import *
from economy.pig6economy import *
from telegram.error import BadRequest, Forbidden

logger = logging.getLogger(__name__)


def ban(s):
    try:
        config = load_config()
        if s not in config["banned_users"]:
            config["banned_users"].append(s)
        save_config(config)
        logger.info("Banned user signature: %s", s)
    except (OSError, ValueError, KeyError) as e:
        logger.exception("Failed to ban %s: %s", s, e)


def unban(s):
    try:
        config = load_config()
        if s in config["banned_users"]:
            config["banned_users"].remove(s)
        save_config(config)
        logger.info("Unbanned user signature: %s", s)
    except (OSError, ValueError, KeyError) as e:
        logger.exception("Failed to unban %s: %s", s, e)


def setbaseprompt(s):
    try:
        config = load_config()
        config["base_prompt"] = s
        save_config(config)
        logger.info("Base prompt updated")
    except (OSError, ValueError, KeyError) as e:
        logger.exception("Failed to set base prompt: %s", e)


async def blockall(context, msg, x=1):
    name = str(MAIN_CHANNEL_ID)

    try:
        config = load_config()
        config["ban_messages"] = "all"
        save_config(config)
    except (OSError, ValueError, KeyError) as e:
        logger.exception("Failed to persist blockall config: %s", e)
        return

    try:
        await context.bot.send_message(
            chat_id=name,
            text=(
                "🟠 Активирован режим полной блокировки.\n\n"
                "Все новые сообщения будут автоматически удаляться."
            ),
        )
    except (BadRequest, Forbidden) as e:
        logger.warning("Failed to announce blockall in channel %s: %s", name, e)

    logger.info("Blockall (full lockdown) activated")

    if msg:
        try:
            await msg.reply_text("🟢 Защита активирована.")
        except (BadRequest, Forbidden) as e:
            logger.warning("Failed to reply to blockall command: %s", e)


async def disable(context, msg):
    name = str(MAIN_CHANNEL_ID)

    try:
        config = load_config()
        config["ban_messages"] = "off"
        save_config(config)
    except (OSError, ValueError, KeyError) as e:
        logger.exception("Failed to persist disable config: %s", e)
        return

    try:
        await context.bot.send_message(
            chat_id=name,
            text=("⚪ Защита отключена."),
        )
    except (BadRequest, Forbidden) as e:
        logger.warning("Failed to announce disable in channel %s: %s", name, e)

    logger.info("Protection disabled")

    if msg:
        try:
            await msg.reply_text("⚪ Защита деактивирована.")
        except (BadRequest, Forbidden) as e:
            logger.warning("Failed to reply to disable command: %s", e)


async def EXCOMMUNICADO(context, msg, targetname=""):
    try:
        config = load_config()
        config["mode"] = "Judgment Day"
        save_config(config)
    except (OSError, ValueError, KeyError) as e:
        logger.exception("Failed to persist Judgment Day mode: %s", e)
        return

    logger.info("Judgment Day protocol activated (target=%s)", targetname)

    try:
        await context.bot.send_message(
            chat_id=MAIN_CHANNEL_ID,
            text=(
                "🔴 Активирован протокол «Judgment Day».\n\n"
                "Защита переведена в максимальный режим.\n"
                "Доступ к каналу ограничен."
                f"\n\nКод подтверждения: {config['Judgment Day Code']}"
            ),
        )
    except (BadRequest, Forbidden) as e:
        logger.warning("Failed to announce Judgment Day start: %s", e)

    await asyncio.sleep(1)
    name = targetname
    for i in config["admins"]:
        if (msg and i["name"] in msg.reply_to_message.author_signature) or (
            i["name"] in name
        ):
            name = i["name"]

    for i in range(5, 0, -1):
        try:
            config = load_config()
        except (OSError, ValueError) as e:
            logger.exception(
                "Failed to reload config during Judgment Day countdown: %s", e
            )
            continue

        try:
            await context.bot.send_message(
                chat_id=MAIN_CHANNEL_ID,
                text=(
                    f"{name} EXCOMMUNICADO {i}\n\n"
                    f"Код подтверждения: {config['Judgment Day Code']}"
                ),
            )
        except (BadRequest, Forbidden) as e:
            logger.warning("Failed to send countdown message (%s): %s", i, e)

        await asyncio.sleep(1)

    try:
        config = load_config()
    except (OSError, ValueError) as e:
        logger.exception("Failed to reload config before excommunication: %s", e)
        config = None

    if config is not None:
        for i in config["admins"]:
            if (msg and i["name"] in msg.reply_to_message.author_signature) or (
                i["name"] in targetname
            ):
                i["EXCOMMUNICADO"] = True
                try:
                    save_config(config)
                except (OSError, ValueError) as e:
                    logger.exception(
                        "Failed to persist excommunication for %s: %s", i["name"], e
                    )

                logger.info("Channel %s marked as EXCOMMUNICADO", i["name"])

                try:
                    if i["protected"]:
                        await context.bot.send_message(
                            i["channel_id"],
                            "⚫ Вы объявлены EXCOMMUNICADO\nДоступ к сервисам «Свиньи-6» отныне закрыт для Вас.",
                        )
                except (BadRequest, Forbidden) as e:
                    if i["protected"]:
                        logger.warning(
                            "Failed to notify excommunicated channel %s: %s",
                            i["channel_id"],
                            e,
                        )

                try:
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
                except (BadRequest, Forbidden) as e:
                    logger.warning(
                        "Failed to announce excommunication of %s: %s", i["name"], e
                    )

    await asyncio.sleep(1)

    try:
        config = load_config()
        config["mode"] = "normal"
        save_config(config)
    except (OSError, ValueError, KeyError) as e:
        logger.exception("Failed to restore normal mode after Judgment Day: %s", e)
        return

    emoji = "⚪"
    if config["ban_messages"] == "all":
        emoji = "🟠"
    elif config["ban_messages"] == "manual":
        emoji = "🟡"

    logger.info("Judgment Day protocol ended, mode restored to normal")

    try:
        await context.bot.send_message(
            chat_id=MAIN_CHANNEL_ID,
            text=(
                f"{emoji} Протокол «Judgment Day» остановлен.\n"
                "Система работает в штатном режиме.\n\n"
                f"Код подтверждения: {config['Judgment Day Code']}"
            ),
        )
    except (BadRequest, Forbidden) as e:
        logger.warning("Failed to announce Judgment Day end: %s", e)


async def jday(context, msg):
    name = str(MAIN_CHANNEL_ID)

    try:
        config = load_config()
    except (OSError, ValueError) as e:
        logger.exception("Failed to load config in jday(): %s", e)
        return

    if config["mode"] == "normal":
        try:
            await context.bot.send_message(
                chat_id=name,
                text=(
                    "🔴 Активирован протокол «Judgment Day».\n\n"
                    "Защита переведена в максимальный режим.\n"
                    "Доступ к каналу ограничен."
                    f"\n\nКод подтверждения: {config['Judgment Day Code']}"
                ),
            )
        except (BadRequest, Forbidden) as e:
            logger.warning("Failed to announce Judgment Day start (jday): %s", e)

        config["mode"] = "Judgment Day"
        logger.info("Judgment Day mode set via jday()")

        if msg:
            try:
                await msg.reply_text(f"🔴 Протокол судного дня активирован")
            except (BadRequest, Forbidden) as e:
                logger.warning("Failed to reply to jday activation: %s", e)

    else:
        emoji = "⚪"
        if config["ban_messages"] == "all":
            emoji = "🟠"
        elif config["ban_messages"] == "manual":
            emoji = "🟡"

        try:
            await context.bot.send_message(
                chat_id=name,
                text=(
                    f"{emoji} Протокол «Judgment Day» остановлен.\n"
                    "Система работает в штатном режиме.\n\n"
                    f"Код подтверждения: {config['Judgment Day Code']}"
                ),
            )
        except (BadRequest, Forbidden) as e:
            logger.warning("Failed to announce Judgment Day end (jday): %s", e)

        config["mode"] = "normal"
        logger.info("Normal mode restored via jday()")

        if msg:
            try:
                await msg.reply_text(f"🟢 Протокол судного дня деактивирован")
            except (BadRequest, Forbidden) as e:
                logger.warning("Failed to reply to jday deactivation: %s", e)

    try:
        save_config(config)
    except (OSError, ValueError) as e:
        logger.exception("Failed to persist config in jday(): %s", e)


superlist = []

for code in range(0xE0100, 0xE01F0):
    superlist.append(chr(code))


def generate_id():
    return "".join(secrets.choice(superlist) for _ in range(5))
