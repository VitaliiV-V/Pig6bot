import uuid
import tools
import secrets
from config import *
from settings import *
from pathlib import Path
from markovchain import *
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from pig6economy import *
from telegram import (
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

g = Generator()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_name = (await context.bot.get_me()).first_name
    msg = update.message
    if not msg:
        return
    await msg.reply_text(f"Вас приветствует система защиты «{bot_name}».\n")


async def blockall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name
    msg = update.message
    if not msg:
        return

    if user_id == OWNER_ID:
        await tools.blockall(context=context, msg=msg)
    else:

        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def smart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        name = str(MAIN_CHANNEL_ID)
        config = load_config()

        config["ban_messages"] = "manual"

        save_config(config)

        await context.bot.send_message(
            chat_id=name,
            text=f"⚠️ Уведомление от системы защиты «{bot_name}»:\n"
            "Включён интеллектуальный режим модерации.\n"
            "Анализирую поведение, фильтрую спам и поддерживаю порядок.\n"
            "Работаю аккуратно.",
        )

        await msg.reply_text(f"Система защиты «{bot_name}» активирована")
    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу 🍌хаммаааааааам🍌"
        )


async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        name = str(MAIN_CHANNEL_ID)
        config = load_config()

        config["ban_messages"] = "off"

        save_config(config)

        await context.bot.send_message(
            chat_id=name,
            text=f"⚠️ Уведомление от системы защиты «{bot_name}»:\n"
            "Система деактивирована.\n"
            "Контроль временно снят.",
        )

        await msg.reply_text(f"Система защиты «{bot_name}» деактивирована")

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
        )


requests = {}


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    if not msg.reply_to_message:
        await msg.reply_text("Пожалуйста, ответьте командой /download на медиафайл")
        return

    gif = msg.reply_to_message.animation
    img = msg.reply_to_message.photo
    video = msg.reply_to_message.video

    if not gif and not img and not video:
        await msg.reply_text("Это не медиафайл")
        return

    request_id = len(requests) + 1
    if gif:
        requests[request_id] = {
            "user_id": msg.from_user.id,
            "file_id": gif.file_id,
            "username": msg.from_user.username,
            "status": "pending",
            "type": "gif",
        }
    elif img:
        requests[request_id] = {
            "user_id": msg.from_user.id,
            "file_id": img[-1],
            "username": msg.from_user.username,
            "status": "pending",
            "type": "img",
        }
    elif video:
        requests[request_id] = {
            "user_id": msg.from_user.id,
            "file_id": video,
            "username": msg.from_user.username,
            "status": "pending",
            "type": "video",
        }
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Accept", callback_data=f"approve^{request_id}"
                ),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject^{request_id}"),
            ]
        ]
    )

    await msg.reply_text(text=(f"{OWNER_USERNAME}"), reply_markup=keyboard)


async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    bot_name = (await context.bot.get_me()).first_name

    if query.from_user.id != OWNER_ID:
        await query.answer(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
        )
        return

    await query.answer()

    action, data = query.data.split("^")

    if action == "approve":
        request_id = int(data)

        req = requests.get(request_id)
        if req["type"] == "gif":
            await context.bot.send_animation(
                chat_id=req["user_id"], animation=req["file_id"], caption="Ваш GIF"
            )
            await query.edit_message_text("✅ GIF отправлен пользователю")
        elif req["type"] == "img":
            await context.bot.send_photo(
                chat_id=req["user_id"], photo=req["file_id"], caption="Ваше изображение"
            )
            await query.edit_message_text("✅ Изображение отправлено пользователю")
        elif req["type"] == "video":
            await context.bot.send_video(
                chat_id=req["user_id"], video=req["file_id"], caption="Ваша видеозапись"
            )
            await query.edit_message_text("✅ Видеозапись отправлена пользователю")
        req["status"] = "approved"

    elif action == "reject":

        request_id = int(data)

        req = requests.get(request_id)
        req["status"] = "rejected"

        await context.bot.send_message(
            chat_id=req["user_id"], text="❌ Ваш запрос отклонён"
        )

        await query.edit_message_text("❌ Запрос отклонён")

    elif action == "protectc":
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
                chat_id=data2["channel_id"], text="Канал под защитой"
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="✅ Канал защищён",
                reply_to_message_id=query.message.message_id,
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ Ошибка",
                reply_to_message_id=query.message.message_id,
            )
    elif action == "rejectc":
        try:
            with open(data, "r", encoding="utf-8") as f:
                data2 = json.load(f)
            os.remove(data)
            await context.bot.send_message(
                chat_id=data2["channel_id"], text="Ваш запрос отклонён"
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="✅ Отклонено",
                reply_to_message_id=query.message.message_id,
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="❌ Ошибка",
                reply_to_message_id=query.message.message_id,
            )


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

        try:
            tools.ban(s)

            await msg.reply_text(f"{s} зaблокирован")
        except Exception as e:
            await msg.reply_text(f"Не удалось зблокировать {s}")

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

        try:
            tools.unban(s)
            await msg.reply_text(f"{s} разблокирован")
        except Exception as e:
            await msg.reply_text(f"Не удалось разблокировать {s}")

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def setwhitelistsmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

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

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def addtolists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

        try:
            config = load_config()
            if s not in config["white_list"]:
                config["white_list"].append(s)

            save_config(config)

            await msg.reply_text(
                f"{s} в белом списке", reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            await msg.reply_text(
                f"Не удалось добавить {s} в белый список",
                reply_markup=ReplyKeyboardRemove(),
            )

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу",
            reply_markup=ReplyKeyboardRemove(),
        )


async def delfromlists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

        try:
            config = load_config()
            config["white_list"].remove(s)

            save_config(config)

            await msg.reply_text(f"{s} больше не в белом списке")
        except Exception as e:
            await msg.reply_text(f"Не удалось убрать {s} из белого списка")

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""
    text = (
        f"Новый запрос на регистрацию канала:\n"
        f"Владелец: {msg.from_user.first_name} @{msg.from_user.username}\n"
        f"Имя канала: {s}"
    )
    keyboard = ReplyKeyboardMarkup([[f"/add {s}", "/reject"]], resize_keyboard=True)
    await context.bot.send_message(chat_id=OWNER_ID, text=text, reply_markup=keyboard)
    await msg.reply_text(
        f"Запрос на регистрацию отправлен", reply_markup=ReplyKeyboardRemove()
    )


async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:
        await msg.reply_text(f"Отклонено", reply_markup=ReplyKeyboardRemove())

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def setfreq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

        try:
            config = load_config()
            config["freq"] = int(s)
            save_config(config)

            await msg.reply_text(
                f"Установлена частота: {s}", reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            await msg.reply_text(
                f"Не удалось установить частоту", reply_markup=ReplyKeyboardRemove()
            )

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу",
            reply_markup=ReplyKeyboardRemove(),
        )


async def pig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user_id = msg.from_user.id

    ans = g.gen(6, 10)
    text = f"{msg.from_user.first_name} @{msg.from_user.username} решил поиграть с ботом и получил ответ: <pre>{ans}</pre>\n"

    if user_id != OWNER_ID:
        await context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="HTML")

    await msg.reply_text(ans)


async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name
    msg = update.message
    if not msg:
        return

    if user_id == OWNER_ID:
        name = str(MAIN_CHANNEL_ID)

        s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

        await context.bot.send_message(chat_id=name, text=s)

        await msg.reply_text(f"Пост отправлен ✅")

    else:

        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def jday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name
    msg = update.message
    if not msg:
        return

    if user_id == OWNER_ID:
        name = str(MAIN_CHANNEL_ID)
        config = load_config()
        status = "активен"
        if config["mode"] == "normal":
            await context.bot.send_message(
                chat_id=name,
                text=f"Системное уведомление «{bot_name}»:\n"
                "Активирован протокол «Judgment Day».\n"
                "Все сообщения в канале и чате будут уничтожены.\n"
                "Доступ пользователей аннулирован.\n"
                "Попытки обхода бесполезны.\n"
                "Канал изолирован и находится под полным контролем.\n"
                f"Код подтверждения: {config['Judgment Day Code']}",
            )
            config["mode"] = "Judgment Day"

        else:
            await context.bot.send_message(
                chat_id=name,
                text=f"Системное уведомление «{bot_name}»:\n"
                "Протокол «Judgment Day» остановлен.\n"
                f"Код подтверждения: {config['Judgment Day Code']}",
            )
            config["mode"] = "normal"
            status = "остановлен"

        save_config(config)
        await msg.reply_text(f"Протокол судного дня {status}")

    else:

        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def jdaycode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name
    msg = update.message
    if not msg:
        return

    if user_id == OWNER_ID:
        config = load_config()

        await msg.reply_text(
            f"<code>Код подтвердения: {config['Judgment Day Code']}</code>",
            parse_mode="HTML",
        )

    else:

        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def svo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    await msg.reply_text(f"Данная команда поддерживается только в мессенджере МАКС\n")


async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return
    if "/config" not in msg.text:
        return
    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name
    msg = update.message
    if not msg:
        return

    if user_id == OWNER_ID:
        document = update.message.document
        if document:
            file = await document.get_file()
            await file.download_to_drive("config.json")
        else:
            await context.bot.send_document(
                chat_id=msg.chat_id, document=open("config.json", "rb")
            )
    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def receive_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name
    msg = update.message
    if not msg:
        return

    if user_id == OWNER_ID:
        document = update.message.document
        if document:
            file = await document.get_file()
            await file.download_to_drive("config.json")

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
        )


async def set_base_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

        try:
            tools.setbaseprompt(s)
            await msg.reply_text(
                f"Базовый промпт обновлён", reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            await msg.reply_text(
                f"Не удалось установить частоту", reply_markup=ReplyKeyboardRemove()
            )

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу",
            reply_markup=ReplyKeyboardRemove(),
        )


async def anon_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""

        try:
            config = load_config()
            if s != "0" and s != "1":
                raise "шлюха"

            config["anon_enable"] = int(s)
            save_config(config)
            await msg.reply_text(f"Успешно")
        except Exception as e:
            await msg.reply_text(f"Ошибка", reply_markup=ReplyKeyboardRemove())

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу",
            reply_markup=ReplyKeyboardRemove(),
        )


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    economy = Pig6Economy()
    config = load_config()

    if economy.get_balance(user_id) < config["cost"]:
        await msg.reply_text(
            text=(
                "❌ <b>Покупка невозможна</b>\n\n"
                f"💰 Требуется: <b>{config['cost']} P6T</b>\n"
                f"📦 Ваш баланс: <b>{economy.get_balance(user_id)} P6T</b>\n\n"
                "Пополните баланс и попробуйте снова."
            ),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )
    else:
        superlist = []

        for code in range(0xE0100, 0xE01F0):
            superlist.append(chr(code))

        code = "".join(secrets.choice(superlist) for _ in range(5))
        await msg.reply_text(
            text=(
                "✅ <b>Покупка завершена</b>\n\n"
                f"Списано: <b>{config['cost']} P6T</b>\n\n"
                f"Остаток на счёте: <b>{economy.get_balance(user_id) - config['cost']} P6T</b>\n\n"
                "Ваш одноразовый код:\n"
                f"◆<code>⠀{code}⠀</code>◆\n\n"
                "Вставьте его в сообщение, которое хотите отправить анонимно.\n\n"
                "После использования код станет недействительным.\n\n"
                "⚠️ Если сообщение будет отклонено системой модерации Свиньи-6, "
                "возврат средств не предусмотрен."
            ),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )

        config = load_config()
        config["anon_codes"].append(code)
        save_config(config)
        file = "codes.json"

        if os.path.exists(file):
            with open(file, "r") as f:
                data = json.load(f)
        else:
            data = {}

        data[code] = [msg.from_user.id, msg.from_user.username]

        with open(file, "w") as f:
            json.dump(data, f, indent=4)

        economy = Pig6Economy()
        economy.create_transaction(
            msg.from_user.id, 0, config["cost"], "buy a anon code"
        )
        economy.close()


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg or not msg.from_user:
        return

    user_id = msg.from_user.id

    economy = Pig6Economy()
    balance = economy.get_balance(user_id)
    economy.close()

    await msg.reply_text(
        text=("💳 <b>Баланс</b>\n\n" f"💰 Доступно: <b>{balance} P6T</b>"),
        parse_mode="HTML",
    )


async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg or not msg.from_user or not msg.text:
        return

    args = msg.text.split()

    if len(args) != 3:
        if not msg.reply_to_message:
            await msg.reply_text("❌ Формат:\n/pay @username количество")
            return
        else:
            target_username = f"@{msg.reply_to_message.from_user.username}"
            try:
                amount = int(args[1])
            except ValueError:
                await msg.reply_text("❌ Количество должно быть числом.")
                return
    else:
        target_username = args[1]

        try:
            amount = int(args[2])
        except ValueError:
            await msg.reply_text("❌ Количество должно быть числом.")
            return

    config = load_config()

    receiver_id = None
    receiver_name = None

    users = config.get("protected_users", []) + config.get("super_users", [])

    for user in users:
        if user["owner"] == target_username:
            receiver_id = int(user["id"])
            receiver_name = user["owner"]
            break

    if receiver_id is None:
        await msg.reply_text("❌ Пользователь не найден.")
        return

    sender_id = msg.from_user.id

    economy = Pig6Economy()

    if economy.get_balance(sender_id) < amount:
        await msg.reply_text("❌ Недостаточно средств.")
        economy.close()
        return

    if not economy.user_exists(receiver_id):
        economy.add_user(receiver_id, 0)

    success = economy.create_transaction(
        sender_id, receiver_id, amount, "user transfer"
    )

    economy.close()

    if not success:
        await msg.reply_text("❌ Не удалось выполнить перевод.")
        return

    await msg.reply_text(
        text=(
            "✅ <b>Перевод выполнен</b>\n\n"
            f"👤 Получатель: <b>{receiver_name}</b>\n"
            f"💰 Сумма: <b>{amount} P6T</b>\n\n"
            "Средства успешно отправлены."
        ),
        parse_mode="HTML",
    )

    try:
        await context.bot.send_message(
            chat_id=receiver_id,
            text=(
                "💳 <b>Новое поступление</b>\n\n"
                f"💰 Вам отправлено: <b>{amount} P6T</b>\n"
                f"👤 От пользователя: <b>@{msg.from_user.username}</b>"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        args = msg.text.split()

        if len(args) != 3:
            if not msg.reply_to_message:
                await msg.reply_text("❌ Формат:\n/give @username количество")
                return
            else:
                target_username = f"@{msg.reply_to_message.from_user.username}"
                try:
                    amount = int(args[1])
                except ValueError:
                    await msg.reply_text("❌ Количество должно быть числом.")
                    return
        else:
            target_username = args[1]

            try:
                amount = int(args[2])
            except ValueError:
                await msg.reply_text("❌ Количество должно быть числом.")
                return

        config = load_config()

        receiver_id = None
        receiver_name = None

        users = config.get("protected_users", []) + config.get("super_users", [])

        for user in users:
            if user["owner"] == target_username:
                receiver_id = int(user["id"])
                receiver_name = user["owner"]
                break

        if receiver_id is None:
            await msg.reply_text("❌ Пользователь не найден.")
            return

        economy = Pig6Economy()

        if not economy.user_exists(receiver_id):
            economy.add_user(receiver_id, 0)

        success = economy.create_transaction(0, receiver_id, amount, "user transfer")

        economy.close()

        if not success:
            await msg.reply_text("❌ Не удалось выполнить перевод.")
            return

        await msg.reply_text(
            text=(
                "✅ <b>Подарок выдан</b>\n\n"
                f"👤 Получатель: <b>{receiver_name}</b>\n"
                f"💰 Сумма: <b>{amount} P6T</b>"
            ),
            parse_mode="HTML",
        )

        try:
            await context.bot.send_message(
                chat_id=receiver_id,
                text=(
                    "💳 <b>Новое поступление</b>\n\n"
                    f"💰 Вам отправлено: <b>{amount} P6T</b>\n"
                    f"👤 От пользователя: SYSTEM"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу",
            reply_markup=ReplyKeyboardRemove(),
        )
