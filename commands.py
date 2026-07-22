import uuid
import tools
from config import *
from settings import *
from pathlib import Path
from markovchain import *
from telegram import Update
from telegram.ext import ContextTypes
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup

g = Generator()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_name = (await context.bot.get_me()).first_name
    msg = update.message
    if not msg:
        return
    await msg.reply_text(
        f"Вас приветствует система защиты «{bot_name}».\n"
    )

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

        await context.bot.send_message(chat_id=name,
                                       text=f"⚠️ Уведомление от системы защиты «{bot_name}»:\n"
                                            "Включён интеллектуальный режим модерации.\n"
                                            "Анализирую поведение, фильтрую спам и поддерживаю порядок.\n"
                                            "Работаю аккуратно.")

        await msg.reply_text(
            f"Система защиты «{bot_name}» активирована"
        )
    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу 🍌хаммаааааааам🍌"
        )



requests = {}

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    if not msg.reply_to_message:
        await msg.reply_text("Пожалуйста, ответьте командой /download на GIF")
        return
    
    gif = msg.reply_to_message.animation
    
    if not gif:
        await msg.reply_text("Это не GIF")
        return

    request_id = len(requests) + 1

    requests[request_id] = {
        "user_id": msg.from_user.id,
        "file_id": gif.file_id,
        "username": msg.from_user.username,
        "status": "pending"
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Accept",
                callback_data=f"approve:{request_id}"
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"reject:{request_id}"
            )
        ]
    ])

    await msg.reply_text(
        text=(
            f"{OWNER_USERNAME}"
        ),
        reply_markup=keyboard
    )

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    bot_name = (await context.bot.get_me()).first_name

    if query.from_user.id != OWNER_ID:
        await query.answer(f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу")
        return

    await query.answer()

    action, request_id = query.data.split(":")
    request_id = int(request_id)

    req = requests.get(request_id)



    if action == "approve":

        await context.bot.send_animation(
            chat_id=req["user_id"],
            animation=req["file_id"],
            caption="Ваш GIF"
        )

        req["status"] = "approved"

        await query.edit_message_text(
            "✅ GIF отправлен пользователю"
        )


    elif action == "reject":

        req["status"] = "rejected"

        await context.bot.send_message(
            chat_id=req["user_id"],
            text="❌ Ваш запрос отклонён"
        )

        await query.edit_message_text(
            "❌ Запрос отклонён"
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

        await context.bot.send_message(chat_id=name,
                                       text=f"⚠️ Уведомление от системы защиты «{bot_name}»:\n"
                                            "Система деактивирована.\n"
                                            "Контроль временно снят.")

        await msg.reply_text(
            f"Система защиты «{bot_name}» деактивирована"
        )

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
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

            await msg.reply_text(
                f"{s} зaблокирован"
            )
        except Exception as e:
            await msg.reply_text(
                f"Не удалось зблокировать {s}"
            )

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
            await msg.reply_text(
                f"{s} разблокирован"
            )
        except Exception as e:
            await msg.reply_text(
                f"Не удалось разблокировать {s}"
            )

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
                await msg.reply_text(
                    f"Успешно"
                )
            except Exception as e:
                await msg.reply_text(
                    f"Failed"
                )
        else:
            await msg.reply_text(
                f"Failed"
            )

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
                f"{s} в белом списке",reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            await msg.reply_text(
                f"Не удалось добавить {s} в белый список",reply_markup=ReplyKeyboardRemove()
            )

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу", reply_markup=ReplyKeyboardRemove()
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

            await msg.reply_text(
                f"{s} больше не в белом списке"
            )
        except Exception as e:
            await msg.reply_text(
                f"Не удалось убрать {s} из белого списка"
            )

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
    text = (f"Новый запрос на регистрацию канала:\n"
            f"Владелец: {msg.from_user.first_name} @{msg.from_user.username}\n"
            f"Имя канала: {s}")
    keyboard = ReplyKeyboardMarkup(
        [[f"/add {s}", "/reject"]],
        resize_keyboard=True
    )
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text = text,
        reply_markup=keyboard
    )
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
        await msg.reply_text(
            f"Отклонено",reply_markup=ReplyKeyboardRemove()
        )

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
                f"Установлена частота: {s}",reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            await msg.reply_text(
                f"Не удалось установить частоту",reply_markup=ReplyKeyboardRemove()
            )

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу", reply_markup=ReplyKeyboardRemove()
        )
        
async def pig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    
    user_id = msg.from_user.id
    
    ans = g.gen(6,10)
    text = f"{msg.from_user.first_name} @{msg.from_user.username} решил поиграть с ботом и получил ответ: <pre>{ans}</pre>\n"
    
    if user_id != OWNER_ID:
        await context.bot.send_message(chat_id=OWNER_ID, text = text, parse_mode="HTML")
    
    await msg.reply_text(
        ans
    )
    
    
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
        
        await msg.reply_text(
            f"Пост отправлен ✅"
        )

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
                f"Код подтверждения: {config['Judgment Day Code']}"
            )
            config["mode"] = "Judgment Day"
            
        else:            
            await context.bot.send_message(
                chat_id=name,
                text=f"Системное уведомление «{bot_name}»:\n"
                "Протокол «Judgment Day» остановлен.\n"                
                f"Код подтверждения: {config['Judgment Day Code']}"
            )
            config["mode"] = "normal"
            status = "остановлен"
            
        save_config(config)
        await msg.reply_text(
            f"Протокол судного дня {status}"
        )

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
            parse_mode="HTML"
        )

    else:

        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}» отражена попытка несанкционированного доступа к телеграм каналу"
        )
        
async def svo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    await msg.reply_text(
        f"Данная команда поддерживается только в мессенджере МАКС\n"
    )
    
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
            config = load_config()
        else:
            await context.bot.send_document(
                chat_id=msg.chat_id,
                document=open("config.json", "rb")
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
            config = load_config()

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
                f"Базовый промпт обновлён",reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            await msg.reply_text(
                f"Не удалось установить частоту",reply_markup=ReplyKeyboardRemove()
            )

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу", reply_markup=ReplyKeyboardRemove()
        )
        


def rand():
    return chr(0xAC00 + (uuid.uuid4().int % (0xD7A3 - 0xAC00 + 1)))

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:


        s = msg.text.split(maxsplit=1)[1] if len(msg.text.split(maxsplit=1)) > 1 else ""
        id = ""
        for i in s:
            if i == ' ':
                break
            id += i

        try:
            config = load_config()
            new_uuid = rand() + str(uuid.uuid4())
            config["protected_users"].append({
                "name" : s[(len(id) + 1):],
                "uuid" : new_uuid,
                "channel_id" : int(id)
            })
            if s[(len(id) + 1):] in config["white_list"]:
                config["white_list"].remove(s[(len(id) + 1):])

            save_config(config)

            await msg.reply_text(
                f"Успешно", reply_markup=ReplyKeyboardRemove()
            )

            await context.bot.set_chat_title(id , s[(len(id) + 1):] + "ㅤㅤㅤㅤㅤㅤ ㅤ ㅤ ㅤ ㅤ ㅤ ㅤ ㅤ " + new_uuid)

            await context.bot.send_message(chat_id=id, text = "Канал под защитой")

        except Exception as e:
            await msg.reply_text(
                f"Ошибка",reply_markup=ReplyKeyboardRemove()
            )

    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу", reply_markup=ReplyKeyboardRemove()
        )