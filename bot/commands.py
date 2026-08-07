import secrets
from bot.panel import *
import bot.tools as tools
from bot.settings import *
from config.config import *
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message
    if not msg:
        return
    await msg.reply_text(
        f"Вас приветствует система защиты «{(await context.bot.get_me()).first_name}».\n"
    )


async def blockallh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not await check_id(msg.from_user.id, msg, context):
        return
    await tools.blockall(context=context, msg=msg)


async def smart(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def fdisable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    await tools.disable(context, msg)


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        await msg.reply_text("Пожалуйста, ответьте командой /download на медиафайл")
        return

    gif = msg.reply_to_message.animation
    img = msg.reply_to_message.photo
    video = msg.reply_to_message.video

    if not gif and not img and not video:
        await msg.reply_text("Это не медиафайл")
        return

    code = secrets.token_hex(8)

    os.makedirs("tmp", exist_ok=True)

    path = f"tmp/.download_{code}.json"

    if gif:

        data = {
            "user_id": msg.from_user.id,
            "file_id": gif.file_id,
            "username": msg.from_user.username,
            "status": "pending",
            "type": "gif",
        }

    elif img:

        data = {
            "user_id": msg.from_user.id,
            "file_id": img[-1].file_id,
            "username": msg.from_user.username,
            "status": "pending",
            "type": "img",
        }

    elif video:

        data = {
            "user_id": msg.from_user.id,
            "file_id": video.file_id,
            "username": msg.from_user.username,
            "status": "pending",
            "type": "video",
        }

    else:

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
            os.remove(data)
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
            req["status"] = "approved"
        else:
            await query.answer("🔴 Доступ запрещён.", show_alert=False)
    elif action == "reject":
        if await check_id(user_id=query.from_user.id, msg=query, context=context):
            with open(data, "r", encoding="utf-8") as f:
                req = json.load(f)
            os.remove(data)
            await context.bot.send_message(
                chat_id=req["user.id"], text="🔴 Ваш запрос отклонён."
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
                config["protected_users"].append(data2)
                save_config(config)
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
    elif action == "panel":
        await panel(update, context)
    await query.answer()


async def fban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

    try:
        tools.ban(s)

        await msg.reply_text(f"🟢 {s} зaблокирован")
    except Exception as e:
        await msg.reply_text(f"🔴 Не удалось заблокировать {s}")


async def funban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

    try:
        tools.unban(s)
        await msg.reply_text(f"🟢 {s} разблокирован")
    except Exception as e:
        await msg.reply_text(f"🔴 Не удалось разблокировать {s}")


async def setwhitelistsmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""
    if s == "admins" or s == "admins_only" or s == "manual" or s == "off":
        try:
            config = load_config()
            config["white_lists_mode"] = s
            save_config(config)
            await msg.reply_text(f"Успешно")
        except Exception as e:
            await msg.reply_text(f"Failed")
    else:
        await msg.reply_text(f"Failed")


async def addtolists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

    try:
        config = load_config()
        if s not in config["white_list"]:
            config["white_list"].append(s)

        save_config(config)

        await msg.reply_text(
            f"🟢 {s} в белом списке", reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        await msg.reply_text(
            f"🔴 Не удалось добавить {s} в белый список",
            reply_markup=ReplyKeyboardRemove(),
        )


async def delfromlists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

    try:
        config = load_config()
        config["white_list"].remove(s)

        save_config(config)

        await msg.reply_text(f"🟢 {s} больше не в белом списке")
    except Exception as e:
        await msg.reply_text(f"🔴 Не удалось убрать {s} из белого списка")


async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    name = str(MAIN_CHANNEL_ID)

    s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

    await context.bot.send_message(chat_id=name, text=s)

    await msg.reply_text(f"🟢 Пост отправлен")


async def fjday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    await tools.jday(context=context, msg=msg)


async def jdaycode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return

    config = load_config()

    await msg.reply_text(
        f"<code>Код подтвердения: {config['Judgment Day Code']}</code>",
        parse_mode="HTML",
    )


async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def receive_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not await check_id(msg.from_user.id, msg, context):
        return
    document = update.message.document
    if document:
        file = await document.get_file()
        await file.download_to_drive("config.json")


async def set_base_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def myaccess(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    for i in config["protected_users"]:
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
