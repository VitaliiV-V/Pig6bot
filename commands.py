from config import *
from markovchain import *
from settings import *
from telegram.ext import ContextTypes
from telegram import Update
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, Update

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
        name = str(MAIN_CHANNEL_ID)
        data = load_config()

        data["ban_messages"] = "all"

        save_config(data)

        await context.bot.send_message(chat_id=name,
                                       text=f"⚠️ Уведомление от системы защиты «{bot_name}»:\n"
                                            "Активирован режим тотальной зачистки.\n"
                                            "Любая активность будет немедленно удалена.\n"
                                            "Канал под полным контролем.")
        await msg.reply_text(
            f"Система защиты «{bot_name}» активирована"
        )

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
        data = load_config()

        data["ban_messages"] = "manual"

        save_config(data)

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

async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name


    if user_id == OWNER_ID:

        name = str(MAIN_CHANNEL_ID)
        data = load_config()

        data["ban_messages"] = "off"

        save_config(data)

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
            
            data = load_config()
            if s not in data["banned_users"]:
                data["banned_users"].append(s)
            save_config(data)

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
            data = load_config()    
            data["banned_users"].remove(s)
            save_config(data)
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
                data = load_config()
                data["white_lists_mode"] = s
                save_config(data)
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
            data = load_config()
            if s not in data["white_list"]:
                data["white_list"].append(s)

            save_config(data)

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
            data = load_config()
            data["white_list"].remove(s)

            save_config(data)

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
            data = load_config()
            data["freq"] = int(s)
            save_config(data)

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
        data = load_config()
        status = "активен"
        if data["mode"] == "normal":           
            await context.bot.send_message(
                chat_id=name,
                text=f"Системное уведомление «{bot_name}»:\n"
                "Активирован протокол «Judgment Day».\n"
                "Все сообщения в канале и чате будут уничтожены.\n"
                "Доступ пользователей аннулирован.\n"
                "Попытки обхода бесполезны.\n"
                "Канал изолирован и находится под полным контролем.\n"
                f"Код подтверждения: {data['Judgment Day Code']}"
            )
            data["mode"] = "Judgment Day"
            
        else:            
            await context.bot.send_message(
                chat_id=name,
                text=f"Системное уведомление «{bot_name}»:\n"
                "Протокол «Judgment Day» остановлен.\n"                
                f"Код подтверждения: {data['Judgment Day Code']}"
            )
            data["mode"] = "normal"
            status = "остановлен"
            
        save_config(data)
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
        data = load_config()

        await msg.reply_text(
            f"<code>Код подтвердения: {data['Judgment Day Code']}</code>",
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
            data = load_config()
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
            data = load_config()

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
            data = load_config()
            data["base_prompt"] = s
            save_config(data)

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
        