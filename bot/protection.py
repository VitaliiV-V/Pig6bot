import bot.tools as tools
import asyncio
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
from contextlib import suppress
from cryptography.hazmat.primitives import serialization

superlist = []
last_time = datetime.now()

for code in range(0xE0100, 0xE01F0):
    superlist.append(chr(code))


def verify_certificate(user_id, text, signature):

    public_path = f"keys/public/{user_id}.public.pem"

    if not os.path.exists(public_path):
        return False

    with open(public_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    payload = f"{user_id}:{text}".encode("utf-8")

    try:
        public_key.verify(bytes.fromhex(signature), payload)
        return True

    except Exception as e:
        return False


async def protect_query(
    context: ContextTypes.DEFAULT_TYPE,
    msg,
    config,
):
    chat_id = msg.chat_id
    if chat_id != MAIN_CHANNEL_ID:
        if msg.new_chat_title:
            with suppress(BadRequest, Forbidden):
                await context.bot.delete_message(
                    chat_id=msg.chat.id, message_id=msg.message_id
                )
        if "protect" == (msg.text or "").lower():
            for i in config["protected_users"]:
                if i["channel_id"] == msg.chat_id:
                    if i["uuid"] == "EXCOMMUNICADO":
                        with suppress(BadRequest, Forbidden):
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text="🔴 Вы EXCOMMUNICADO. Защита канала вам недоступна",
                            )
                    else:
                        with suppress(BadRequest, Forbidden):
                            await context.bot.send_message(
                                chat_id=chat_id, text="🟢 Канал уже под защитой!"
                            )
                    return

            admins = await context.bot.get_chat_administrators(chat_id)

            if len(admins) == 2:
                info = ""
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
                }

                file_id = secrets.token_hex(8)
                try:
                    os.mkdir("tmp")
                except FileExistsError:
                    pass
                filename = f"tmp/.protect_{file_id}.json"

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(protect_data, f, ensure_ascii=False, indent=4)

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

                with suppress(BadRequest, Forbidden):
                    await context.bot.send_message(
                        chat_id=OWNER_ID, text=text, reply_markup=keyboard
                    )

                for id in config["root_users"]:
                    with suppress(BadRequest, Forbidden):
                        await context.bot.send_message(
                            chat_id=id, text=text, reply_markup=keyboard
                        )

                with suppress(BadRequest, Forbidden):
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🟠 Запрос на защиту отправлен.",
                    )
            else:

                with suppress(BadRequest, Forbidden):
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🔴 Регистрация недоступна.\nДля подключения защиты в канале должен быть только один администратор и бот.",
                    )
        if "unprotect" == (msg.text or "").lower():
            try:
                config = load_config()
                config["protected_users"] = [
                    user
                    for user in config["protected_users"]
                    if user["channel_id"] != msg.chat.id
                ]
                save_config(config)

                with suppress(BadRequest, Forbidden):
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🟢 Защита отключена",
                    )
            except Exception as e:
                with suppress(BadRequest, Forbidden):
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
                    if (
                        datetime.now() - last_time
                    ).total_seconds() > 0.5 or not msg.forward_origin:
                        with suppress(BadRequest, Forbidden):
                            await context.bot.delete_message(
                                chat_id=chat_id, message_id=message_id
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
                    except:
                        pass

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

    if "/bangif" in message_text:
        config = load_config()
        config["bad_gifs"].append(msg.reply_to_message.animation.file_id)
        save_config(config)
    elif "/ban" in message_text:
        tools.ban(msg.reply_to_message.author_signature)
    elif "/unban" in message_text:
        tools.unban(msg.reply_to_message.author_signature)
    elif "EXCOMMUNICADO" in message_text:
        await tools.EXCOMMUNICADO(context, msg)

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
            if (
                datetime.now() - last_time
            ).total_seconds() > 0.5 or not msg.forward_origin:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                return False
            return True
        else:
            if "/ban" in message_text:
                tools.ban(msg.reply_to_message.author_signature)
            elif "/unban" in message_text:
                tools.unban(msg.reply_to_message.author_signature)
            elif "/bangif" in message_text:
                config = load_config()
                config["bad_gifs"].append(msg.reply_to_message.animation.file_id)
                save_config(config)
            elif "EXCOMMUNICADO" in message_text:
                await tools.EXCOMMUNICADO(context, msg)
            try:
                new_uuid = tools.generate_id()

                await context.bot.set_chat_title(
                    PERSONAL_CHANNEL_ID, config["owner_name"] + new_uuid
                )

                config = load_config()
                config["uuid"] = new_uuid
                save_config(config)
            except:
                pass
            last_time = datetime.now()
            return True

    return False


async def check_protection(context: ContextTypes.DEFAULT_TYPE, msg, config):
    global last_time
    chat_id = msg.chat_id

    message_id = msg.message_id
    if msg.author_signature:
        for i in config["protected_users"]:
            if i["name"] in msg.author_signature:
                if i["name"] + i["uuid"] != msg.author_signature:
                    if (
                        datetime.now() - last_time
                    ).total_seconds() > 0.5 or not msg.forward_origin:
                        await context.bot.delete_message(
                            chat_id=chat_id, message_id=message_id
                        )
                        return False, 0
                    return True, i["trust"]
                else:
                    if i["mute"] or i["EXCOMMUNICADO"]:
                        await context.bot.delete_message(
                            chat_id=chat_id, message_id=message_id
                        )
                        return False, 0
                    if msg.text == "EXCOMMUNICADO" and not i["trust"]:
                        await tools.EXCOMMUNICADO(
                            context, msg=None, targetname=i["name"]
                        )
                        return False, 0
                    try:
                        new_uuid = tools.generate_id()
                        await context.bot.set_chat_title(
                            i["channel_id"], i["name"] + new_uuid
                        )

                        i["uuid"] = new_uuid
                        save_config(config)
                    except:
                        pass
                    last_time = datetime.now()
                    return True, i["trust"]
    return False, 0
