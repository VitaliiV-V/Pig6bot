import bot.tools as tools
import asyncio
import logging
import secrets
from config.config import *
from bot.settings import *
from datetime import datetime
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from economy.pig6economy import *
import json
import os
from telegram.error import BadRequest, Forbidden
from contextlib import *
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

superlist = []
last_time = datetime.now()

for code in range(0xE0100, 0xE01F0):
    superlist.append(chr(code))


def verify_certificate(user_id, text, signature):
    public_path = f"keys/public/{user_id}.public.pem"

    if not os.path.exists(public_path):
        logger.warning(
            "Public key not found for user_id=%s (path=%s)", user_id, public_path
        )
        return False

    try:
        with open(public_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
    except (OSError, ValueError) as e:
        logger.exception("Failed to load public key for user_id=%s: %s", user_id, e)
        return False

    payload = f"{user_id}:{text}".encode("utf-8")

    try:
        public_key.verify(bytes.fromhex(signature), payload)
        return True
    except Exception as e:
        logger.info("Certificate verification failed for user_id=%s: %s", user_id, e)
        return False


async def protect_query(
    context: ContextTypes.DEFAULT_TYPE,
    msg,
    config,
):
    chat_id = msg.chat_id
    if chat_id != MAIN_CHANNEL_ID:
        if msg.new_chat_title:
            try:
                await context.bot.delete_message(
                    chat_id=msg.chat.id, message_id=msg.message_id
                )
            except Exception as e:
                logger.warning(
                    "Failed to delete message %s in chat %s: %s",
                    msg.message_id,
                    msg.chat.id,
                    e,
                )
                raise

        if "protect" == (msg.text or "").lower():
            for i in config["admins"]:
                if i.get("channel_id") == msg.chat_id:
                    if i["EXCOMMUNICADO"]:
                        try:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text="🔴 Вы EXCOMMUNICADO. Защита канала вам недоступна",
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to notify EXCOMMUNICADO channel %s: %s",
                                chat_id,
                                e,
                            )
                    else:
                        try:
                            await context.bot.send_message(
                                chat_id=chat_id, text="🟢 Канал уже под защитой!"
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to notify already-protected channel %s: %s",
                                chat_id,
                                e,
                            )
                    return

            admins = await context.bot.get_chat_administrators(chat_id)

            if len(admins) == 2:
                info = ""
                info2 = ""
                for admin in admins:
                    if not admin.user.is_bot:
                        info = f"@{admin.user.username}"
                        info2 = f"{admin.user.id}"

                text = f"Новый запрос на защиту канала:\nВладелец: {info}\nКанал: {msg.chat.title}"
                protect_data = {
                    "name": msg.chat.title,
                    "channel_id": msg.chat.id,
                    "uuid": "".join(secrets.choice(superlist) for _ in range(5)),
                    "owner": info,
                    "id": info2,
                    "mute": False,
                    "EXCOMMUNICADO": False,
                    "trust": False,
                    "protected": True,
                }

                file_id = secrets.token_hex(8)
                try:
                    os.mkdir("tmp")
                except FileExistsError:
                    pass
                except OSError as e:
                    logger.exception("Failed to create tmp directory: %s", e)
                    return

                filename = f"tmp/.protect_{file_id}.json"

                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(protect_data, f, ensure_ascii=False, indent=4)
                except OSError as e:
                    logger.exception(
                        "Failed to write protect request file %s: %s", filename, e
                    )
                    return

                keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✅ Accept", callback_data=f"protectc^{filename}"
                            ),
                            InlineKeyboardButton(
                                "❌ Reject", callback_data=f"rejectc^{filename}"
                            ),
                        ]
                    ]
                )

                try:
                    await context.bot.send_message(
                        chat_id=OWNER_ID, text=text, reply_markup=keyboard
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to notify owner %s about protect request: %s",
                        OWNER_ID,
                        e,
                    )

                for id in config["root_users"]:
                    try:
                        await context.bot.send_message(
                            chat_id=id, text=text, reply_markup=keyboard
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to notify root user %s about protect request: %s",
                            id,
                            e,
                        )

                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🟠 Запрос на защиту отправлен.",
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to notify channel %s that request was sent: %s",
                        chat_id,
                        e,
                    )
            else:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🔴 Регистрация недоступна.\nДля подключения защиты в канале должен быть только один администратор и бот.",
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to notify channel %s about registration refusal: %s",
                        chat_id,
                        e,
                    )

        if "unprotect" == (msg.text or "").lower():
            try:
                config = load_config()
                config["admins"] = [
                    user
                    for user in config["admins"]
                    if user["channel_id"] != msg.chat.id
                ]
                save_config(config)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🟢 Защита отключена",
                )
            except Exception as e:
                logger.warning(
                    "Failed to send unprotect confirmation to %s: %s", chat_id, e
                )
            except (OSError, KeyError, ValueError) as e:
                logger.exception("Failed to unprotect channel %s: %s", chat_id, e)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🔴 Ошибка. Возможно Ваш канал не защищён",
                )
        return


async def check_super_user(
    context: ContextTypes.DEFAULT_TYPE,
    msg,
    config,
):
    global last_time
    chat_id = msg.chat_id
    message_id = msg.message_id

    if msg.author_signature:
        for i in config["alpha_users"]:
            if i["name"] in msg.author_signature:
                if i["name"] + i["uuid"] != msg.author_signature:
                    if (datetime.now() - last_time).total_seconds() > 0.5 or (
                        not msg.forward_origin and not msg.photo and not msg.video
                    ):
                        try:
                            await context.bot.delete_message(
                                chat_id=chat_id, message_id=message_id
                            )
                        except Exception as e:
                            logger.error(
                                "Failed to delete unsigned super-user message %s in %s: %s",
                                message_id,
                                chat_id,
                                e,
                            )
                        return False
                    return True
                else:
                    try:
                        new_uuid = tools.generate_id()
                        await context.bot.set_chat_title(
                            i["channel_id"], i["name"] + new_uuid
                        )
                        i["uuid"] = new_uuid
                        save_config(config)
                        last_time = datetime.now()
                    except (BadRequest, Forbidden, OSError, ValueError) as e:
                        logger.exception(
                            "Failed to rotate super-user uuid for channel %s: %s",
                            i.get("channel_id"),
                            e,
                        )

                    return True
    return False


async def check_signed_user(
    context: ContextTypes.DEFAULT_TYPE,
    msg,
    config,
):
    if not msg.text:
        return ""

    message_text = msg.text

    signature = None
    user_id = None

    if msg.entities:
        for entity in msg.entities:
            if entity.type == "text_link":
                url = entity.url

                if "signature=" in url:
                    signature = url.split("signature=")[-1].split("&")[0]

                if "user_id=" in url:
                    user_id = url.split("user_id=")[-1].split("&")[0]

                break

    if not signature:
        return ""

    message_text = message_text.replace(
        "\n\nThis message was signed by Pig-6 Certificates.\nView signature.", ""
    ).strip()

    signed_users = config.get("signed_users", {})

    if user_id and user_id in signed_users:
        user_data = signed_users[user_id]

        if verify_certificate(int(user_id), message_text, signature):
            return user_data["role"]

    for shadow_id, user_data in signed_users.items():
        if "shadow" not in user_data["role"]:
            continue

        if not verify_certificate(int(shadow_id), message_text, signature):
            continue

        if "root" not in user_data.get("role") and str(msg.author_signature) != str(
            shadow_id
        ):
            continue

        return user_data["role"]

    return ""


async def root_commands(context: ContextTypes.DEFAULT_TYPE, msg, config):
    global last_time
    chat_id = msg.chat_id
    message_text = msg.text or ""

    try:
        if "/bangif" in message_text:
            config = load_config()
            config["bad_gifs"].append(msg.reply_to_message.animation.file_id)
            save_config(config)
            logger.info("Root command /bangif executed in chat %s", chat_id)
        elif "/ban" in message_text:
            tools.ban(msg.reply_to_message.author_signature)
            logger.info("Root command /ban executed in chat %s", chat_id)
        elif "/unban" in message_text:
            tools.unban(msg.reply_to_message.author_signature)
            logger.info("Root command /unban executed in chat %s", chat_id)
        elif "EXCOMMUNICADO" in message_text:
            await tools.EXCOMMUNICADO(context, msg)
            logger.info("EXCOMMUNICADO protocol triggered by root in chat %s", chat_id)

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
                chat_id=chat_id,
                text=(
                    f"{emoji} Протокол «Judgment Day» остановлен.\n"
                    "Система работает в штатном режиме.\n\n"
                    f"Код подтверждения: {config['Judgment Day Code']}"
                ),
            )
    except Exception as e:
        logger.warning(
            "Telegram API error while executing root command in chat %s: %s", chat_id, e
        )
    except (AttributeError, KeyError, OSError, ValueError) as e:
        logger.exception("Failed to execute root command in chat %s: %s", chat_id, e)


async def check_owner(
    context: ContextTypes.DEFAULT_TYPE,
    msg,
    config,
):
    global last_time
    chat_id = msg.chat_id
    message_id = msg.message_id
    message_text = msg.text or ""

    bot_name = (await context.bot.get_me()).first_name

    if msg.author_signature and config["owner_name"] in msg.author_signature:
        if msg.author_signature != config["owner_name"] + config["uuid"]:
            if (datetime.now() - last_time).total_seconds() > 0.5 or (
                not msg.forward_origin and not msg.photo and not msg.video
            ):
                try:
                    await context.bot.delete_message(
                        chat_id=chat_id, message_id=message_id
                    )
                except Exception as e:
                    logger.error(
                        "Failed to delete unsigned owner message %s in %s: %s",
                        message_id,
                        chat_id,
                        e,
                    )
                return False
            return True
        else:
            try:
                if "/ban" in message_text:
                    tools.ban(msg.reply_to_message.author_signature)
                    logger.info("Owner command /ban executed in chat %s", chat_id)
                elif "/unban" in message_text:
                    tools.unban(msg.reply_to_message.author_signature)
                    logger.info("Owner command /unban executed in chat %s", chat_id)
                elif "/bangif" in message_text:
                    config = load_config()
                    config["bad_gifs"].append(msg.reply_to_message.animation.file_id)
                    save_config(config)
                    logger.info("Owner command /bangif executed in chat %s", chat_id)
                elif "EXCOMMUNICADO" in message_text:
                    await tools.EXCOMMUNICADO(context, msg)
                    logger.info(
                        "EXCOMMUNICADO protocol triggered by owner in chat %s", chat_id
                    )
            except Exception as e:
                logger.warning(
                    "Telegram API error while executing owner command in chat %s: %s",
                    chat_id,
                    e,
                )
            except (AttributeError, KeyError, OSError, ValueError) as e:
                logger.exception(
                    "Failed to execute owner command in chat %s: %s", chat_id, e
                )

            try:
                new_uuid = tools.generate_id()

                await context.bot.set_chat_title(
                    PERSONAL_CHANNEL_ID, config["owner_name"] + new_uuid
                )

                config = load_config()
                config["uuid"] = new_uuid
                save_config(config)
            except (BadRequest, Forbidden, OSError, ValueError) as e:
                logger.exception("Failed to rotate owner uuid: %s", e)

            last_time = datetime.now()
            return True

    return False


async def check_protection(context: ContextTypes.DEFAULT_TYPE, msg, config):
    global last_time
    chat_id = msg.chat_id
    message_id = msg.message_id

    if msg.author_signature:
        for i in config["admins"]:
            if i["name"] in msg.author_signature:
                if i["name"] + i["uuid"] != msg.author_signature:
                    if (datetime.now() - last_time).total_seconds() > 0.5 or (
                        not msg.forward_origin and not msg.photo and not msg.video
                    ):
                        try:
                            await context.bot.delete_message(
                                chat_id=chat_id, message_id=message_id
                            )
                        except Exception as e:
                            logger.error(
                                "Failed to delete unsigned protected-user message %s in %s: %s",
                                message_id,
                                chat_id,
                                e,
                            )
                        return False, 0
                    return True, i["trust"]
                else:
                    if i["mute"] or i["EXCOMMUNICADO"]:
                        try:
                            await context.bot.delete_message(
                                chat_id=chat_id, message_id=message_id
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to delete message from muted/excommunicated user in %s: %s",
                                chat_id,
                                e,
                            )
                        return False, 0
                    if msg.text == "EXCOMMUNICADO" and not i["trust"]:
                        await tools.EXCOMMUNICADO(
                            context, msg=None, targetname=i["name"]
                        )
                        logger.info(
                            "EXCOMMUNICADO triggered against %s in chat %s",
                            i["name"],
                            chat_id,
                        )
                        return False, 0
                    if i["protected"]:
                        try:
                            new_uuid = tools.generate_id()
                            await context.bot.set_chat_title(
                                i["channel_id"], i["name"] + new_uuid
                            )

                            i["uuid"] = new_uuid
                            save_config(config)
                        except (BadRequest, Forbidden, OSError, ValueError) as e:
                            logger.exception(
                                "Failed to rotate uuid for protected channel %s: %s",
                                i.get("channel_id"),
                                e,
                            )
                        last_time = datetime.now()
                        return True, i["trust"]
                    return True, 0
    return False, 0
