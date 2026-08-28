import secrets
from bot.panel import *
import bot.tools as tools
from bot.settings import *
from config.config import *
from olymp.handlers import *
from economy.economy import *
from economy.pig6economy import *
from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import (
    ReplyKeyboardRemove,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

requests = {}


async def check_id(user_id, msg, context):
    config = load_config()
    if user_id in config["root_users"]:
        return True
    if user_id == OWNER_ID:
        return True
    try:
        await msg.reply_text("🔴 Доступ запрещён.")
    except Exception as e:
        pass
    return False


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message
    if not msg:
        return
    await msg.reply_text(
        f"Вас приветствует система защиты «{(await context.bot.get_me()).first_name}».\n"
    )


async def blockall_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not await check_id(msg.from_user.id, msg, context):
        return
    await tools.blockall(context=context, msg=msg)


async def smart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    name = str(MAIN_CHANNEL_ID)
    config = load_config()

    config["ban_messages"] = "manual"

    save_config(config)

    await context.bot.send_message(
        chat_id=name,
        text=(
            f"🟡 Интеллектуальный режим модерации включён\n\n"
            f"Система защиты анализирует сообщения и автоматически поддерживает порядок."
        ),
    )

    await msg.reply_text("🟢 Защита активирована.")


async def disable_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    await tools.disable(context, msg)


async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        await msg.reply_text("Пожалуйста, ответьте командой /download на медиафайл")
        return

    gif = msg.reply_to_message.animation
    img = msg.reply_to_message.photo
    video = msg.reply_to_message.video
    sticker = msg.reply_to_message.sticker

    if not gif and not img and not video and not sticker:
        await msg.reply_text("Это не медиафайл")
        return

    code = secrets.token_hex(8)

    os.makedirs("tmp", exist_ok=True)

    path = f"tmp/.download_{code}.json"

    if gif:
        data = {
            "user_id": msg.from_user.id,
            "id": str(msg.chat_id) + str(msg.reply_to_message.message_id),
            "file_id": gif.file_id,
            "username": msg.from_user.username,
            "status": "pending",
            "type": "gif",
        }

    elif img:

        data = {
            "user_id": msg.from_user.id,
            "id": str(msg.chat_id) + str(msg.reply_to_message.message_id),
            "file_id": img[-1].file_id,
            "username": msg.from_user.username,
            "status": "pending",
            "type": "img",
        }

    elif video:

        data = {
            "user_id": msg.from_user.id,
            "id": str(msg.chat_id) + str(msg.reply_to_message.message_id),
            "file_id": video.file_id,
            "username": msg.from_user.username,
            "status": "pending",
            "type": "video",
        }

    elif sticker:
        data = {
            "user_id": msg.from_user.id,
            "id": str(msg.chat_id) + str(msg.reply_to_message.message_id),
            "file_id": sticker.file_id,
            "username": msg.from_user.username,
            "status": "pending",
            "type": "sticker",
        }
    else:

        return
    with open("tmp/allowed_messages.json", "r", encoding="utf-8") as f:
        allowed_messages = json.load(f)

    if data["id"] in allowed_messages["messages"]:
        req = data
        if req["type"] == "gif":
            await context.bot.send_animation(
                chat_id=req["user_id"],
                animation=req["file_id"],
                caption="Ваш GIF",
            )
            await msg.reply_text("🟢 GIF отправлен Вам в личные сообщения.")
        elif req["type"] == "img":
            await context.bot.send_photo(
                chat_id=req["user_id"],
                photo=req["file_id"],
                caption="Ваше изображение",
            )
            await msg.reply_text("🟢 Изображение отправлено Вам в личные сообщения.")
        elif req["type"] == "video":
            await context.bot.send_video(
                chat_id=req["user_id"],
                video=req["file_id"],
                caption="Ваша видеозапись",
            )
            await msg.reply_text("🟢 Видеозапись отправлена Вам в личные сообщения.")
        elif req["type"] == "sticker":
            await context.bot.send_sticker(
                chat_id=req["user_id"],
                sticker=req["file_id"],
            )
            await msg.reply_text("🟢 Стикер отправлен Вам в личные сообщения.")
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"approve^{path}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject^{path}"),
            ]
        ]
    )

    await msg.reply_text(text=(f"{OWNER_USERNAME}"), reply_markup=keyboard)


async def buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    parts = query.data.split("^")
    action, data = parts[0], parts[1]

    if action == "approve":
        if await check_id(user_id=query.from_user.id, msg=query, context=context):
            with open(data, "r", encoding="utf-8") as f:
                req = json.load(f)
            if req["type"] == "gif":
                await context.bot.send_animation(
                    chat_id=req["user_id"],
                    animation=req["file_id"],
                    caption="Ваш GIF",
                )
                await query.edit_message_text(
                    "🟢 GIF отправлен Вам в личные сообщения."
                )
            elif req["type"] == "img":
                await context.bot.send_photo(
                    chat_id=req["user_id"],
                    photo=req["file_id"],
                    caption="Ваше изображение",
                )
                await query.edit_message_text(
                    "🟢 Изображение отправлено Вам в личные сообщения."
                )
            elif req["type"] == "video":
                await context.bot.send_video(
                    chat_id=req["user_id"],
                    video=req["file_id"],
                    caption="Ваша видеозапись",
                )
                await query.edit_message_text(
                    "🟢 Видеозапись отправлена Вам в личные сообщения."
                )
            elif req["type"] == "sticker":
                await context.bot.send_sticker(
                    chat_id=req["user_id"],
                    sticker=req["file_id"],
                )
                await query.edit_message_text(
                    "🟢 Стикер отправлен Вам в личные сообщения."
                )
            req["status"] = "approved"
            with open("tmp/allowed_messages.json", "r", encoding="utf-8") as f:
                allowed_messages = json.load(f)
            allowed_messages["messages"].append(req["id"])

            with open("tmp/allowed_messages.json", "w", encoding="utf-8") as f:
                json.dump(
                    allowed_messages,
                    f,
                    ensure_ascii=False,
                    indent=4,
                )
        else:
            await query.answer("🔴 Доступ запрещён.", show_alert=False)
    elif action == "reject":
        if await check_id(user_id=query.from_user.id, msg=query, context=context):
            with open(data, "r", encoding="utf-8") as f:
                req = json.load(f)
            os.remove(data)
            await context.bot.send_message(
                chat_id=req["user_id"], text="🔴 Ваш запрос отклонён."
            )

            await query.edit_message_text("🔴 Запрос отклонён.")
        else:
            await query.answer("🔴 Доступ запрещён.", show_alert=False)
    elif action == "protectc":
        if await check_id(user_id=query.from_user.id, msg=query, context=context):
            try:
                config = load_config()
                with open(data, "r", encoding="utf-8") as f:
                    data2 = json.load(f)
                os.remove(data)
                config["admins"].append(data2)
                save_config(config)
                if data2["protected"]:
                    await context.bot.set_chat_title(
                        data2["channel_id"], data2["name"] + data2["uuid"]
                    )
                    await context.bot.send_message(
                        chat_id=data2["channel_id"],
                        text="🟢 Ваша заявка на защиту канала принята",
                    )
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text="🟢 Канал защищён",
                        reply_to_message_id=query.message.message_id,
                    )
                else:
                    await context.bot.send_message(
                        chat_id=data2["id"],
                        text="🟢 Ваша заявка принята",
                    )
            except Exception as e:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="🔴 Ошибка",
                    reply_to_message_id=query.message.message_id,
                )
        else:
            await query.answer("🔴 Доступ запрещён.", show_alert=False)
    elif action == "rejectc":
        if await check_id(user_id=query.from_user.id, msg=query, context=context):
            try:
                with open(data, "r", encoding="utf-8") as f:
                    data2 = json.load(f)
                os.remove(data)
                await context.bot.send_message(
                    chat_id=data2["channel_id"], text="Ваш запрос отклонён"
                )
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="🟢 Отклонено",
                    reply_to_message_id=query.message.message_id,
                )
            except Exception as e:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="🔴 Ошибка",
                    reply_to_message_id=query.message.message_id,
                )
        else:
            await query.answer("🔴 Доступ запрещён.", show_alert=False)

    elif action == "pay":
        await confirm_pay(query, data, context)
    elif action == "sell":
        await confirm_sell(query, data, context)
    elif action == "panel":
        await panel(update, context)
    elif action == "approveq":
        if await check_id(user_id=query.from_user.id, msg=query, context=context):
            with open(data, "r", encoding="utf-8") as f:
                req = json.load(f)

            sticker_path = req["sticker_path"]

            with open(sticker_path, "rb") as sticker_file:
                await context.bot.send_sticker(
                    chat_id=req["user_id"], sticker=sticker_file
                )
            await query.edit_message_text("🟢 Стикер отправлен Вам в личные сообщения.")
            with open("tmp/allowed_messages.json", "r", encoding="utf-8") as f:
                allowed_messages = json.load(f)
            allowed_messages["messages"].append(req["id"])
            with open("tmp/allowed_messages.json", "w", encoding="utf-8") as f:
                json.dump(
                    allowed_messages,
                    f,
                    ensure_ascii=False,
                    indent=4,
                )
        else:
            await query.answer("🔴 Доступ запрещён.", show_alert=False)
    elif action == "rejectq":
        if await check_id(user_id=query.from_user.id, msg=query, context=context):
            with open(data, "r", encoding="utf-8") as f:
                req = json.load(f)
            os.remove(data)
            await context.bot.send_message(
                chat_id=req["user_id"], text="🔴 Ваш запрос отклонён."
            )

            await query.edit_message_text("🔴 Запрос отклонён.")
        else:
            await query.answer("🔴 Доступ запрещён.", show_alert=False)
    elif action == "olymp":
        await olymp(update, context)
    await query.answer()


async def post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    name = str(MAIN_CHANNEL_ID)

    s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

    await context.bot.send_message(chat_id=name, text=s)

    await msg.reply_text(f"🟢 Пост отправлен")


async def reg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id = msg.chat_id

    if chat_id != msg.from_user.id:
        return

    config = load_config()

    text = f"Новый запрос на админские права от: @{msg.from_user.username}"
    name = f"{msg.from_user.first_name} {msg.from_user.last_name}"
    if not msg.from_user.first_name:
        name = msg.from_user.last_name
    elif not msg.from_user.last_name:
        name = msg.from_user.first_name
    protect_data = {
        "name": name,
        "uuid": "",
        "owner": f"@{msg.from_user.username}",
        "id": f"{msg.from_user.id}",
        "mute": False,
        "EXCOMMUNICADO": False,
        "protected": False,
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
        logger.exception("Failed to write protect request file %s: %s", filename, e)
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"protectc^{filename}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rejectc^{filename}"),
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
            await context.bot.send_message(chat_id=id, text=text, reply_markup=keyboard)
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


async def jday_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    await tools.jday(context=context, msg=msg)


async def jdaycode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return

    config = load_config()

    await msg.reply_text(
        f"<code>Код подтвердения: {config['Judgment Day Code']}</code>",
        parse_mode="HTML",
    )


async def config_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    document = update.message.document
    if document:
        file = await document.get_file()
        await file.download_to_drive("config.json")
    else:
        await context.bot.send_document(
            chat_id=msg.chat_id, document=open("config.json", "rb")
        )


async def receive_config_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    document = update.message.document
    if document:
        file = await document.get_file()
        await file.download_to_drive("config.json")


async def set_base_prompt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return

    s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

    try:
        tools.setbaseprompt(s)
        await msg.reply_text(
            f"🟢 Базовый промпт обновлён", reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        await msg.reply_text(
            f"🔴 Не удалось установить частоту", reply_markup=ReplyKeyboardRemove()
        )


async def myaccess_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    config = load_config()
    if msg.from_user.id in config["root_users"] or msg.from_user.id == OWNER_ID:
        await msg.reply_text(
            text=(
                "<b>🟣 Уровень доступа: ALPHA</b>\n\n"
                "Абсолютный уровень доступа.\n\n"
                "Вам доступны все функции Свиньи-6, управление системой, конфигурацией и уровнями допуска пользователей."
            ),
            parse_mode="HTML",
        )
        return
    for i in config["admins"]:
        if int(i.get("id")) == msg.from_user.id and i.get("trust"):
            await msg.reply_text(
                text=(
                    "<b>🔵 Уровень доступа: TRUST</b>\n\n"
                    "Абсолютный уровень доступа.\n\n"
                    "Во время режима блокировки вы можете продолжать отправлять сообщения."
                ),
                parse_mode="HTML",
            )
            return

    await msg.reply_text(
        text=(
            "<b>⚪ Уровень доступа: CIVIL</b>\n\n"
            "Базовый уровень доступа.\n\n"
            "На вас распространяются все стандартные правила и ограничения системы защиты."
        ),
        parse_mode="HTML",
    )


async def logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    msg = update.message
    config = load_config()
    if msg.from_user.id in config["root_users"] or msg.from_user.id == OWNER_ID:
        await context.bot.send_document(
            chat_id=msg.chat_id, document=open("logs/main.log", "rb")
        )
        return
    for i in config["admins"]:
        if int(i.get("id")) == msg.from_user.id and i.get("trust"):
            await context.bot.send_document(
                chat_id=msg.chat_id, document=open("logs/main.log", "rb")
            )
            return


async def apikey_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    try:

        args = msg.text.split()
        # if len(args) == 1:
        #     await msg.reply_text(
        #         text="Формат использования /apikey <NAME>",
        #     )
        #     return
        # name = (
        #     msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""
        # )
        msg = update.message

        if not msg or not msg.from_user:
            return

        user_id = msg.from_user.id
        user_name = msg.from_user.username

        economy.set_name_if_empty(user_id, user_name)

        api_key = economy.create_api_key(
            user_id=user_id,
            name="Telegram Bot",
        )

        await msg.reply_text(
            text=(
                "🔐 <b>API-доступ Свиньи-6</b>\n\n"
                "Ваш персональный API-ключ создан.\n\n"
                f"<code>{api_key}</code>\n\n"
                "⚠️ <b>Важно:</b> сохраните этот ключ в безопасном месте. "
                "После выхода из этого сообщения получить его повторно "
                "будет невозможно.\n\n"
                "Никому не передавайте Ваш API-ключ."
            ),
            parse_mode="HTML",
        )

        logger.info("API key issued to user %s", user_id)

    except Exception:
        logger.exception("api_handler() failed")
        raise
