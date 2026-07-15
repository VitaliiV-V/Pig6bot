import uuid
import time
import tools
import random
import asyncio
from config import *
from settings import *
from markovchain import *
from datetime import datetime
from telegram.ext import ContextTypes
from telegram import Update, ReplyKeyboardMarkup

g = Generator()

def check(text):

    with open("dict.json", "r", encoding = "utf-8") as f:
        data = json.load(f)

    text = text.lower()
    text2 = ''
    for i in text:
        val = data.get(i)
        if val is not None:
            if len(text2) == 0 or text2[-1] != val:
                text2 += val


    config = load_config()

    for i in config["banned"]:
        if i in text2 or i in text:
            return True

    return False

async def train_background(text):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, g.train, text)

class Message:
    def __init__(self, author_username: str, text: str, message_id: int):
        self.author_username = author_username
        self.text = text
        self.message_id = message_id
        self.created_at = datetime.now()

    def age(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()

messages = []
last_time = datetime.now()

async def reply_in_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_time, messages
    msg = update.channel_post or update.edited_channel_post

    if not msg:
        return
    
    chat_id = msg.chat_id
    message_id = msg.message_id
    message_text = msg.text or ""

    bot_name = (await context.bot.get_me()).first_name

    config = load_config()

    if chat_id != MAIN_CHANNEL_ID:
        if "protect" in (msg.text or "").lower():
            for i in config["protected_users"]:
                if i["channel_id"] == msg.chat_id:
                    if i["uuid"] == "EXCOMMUNICADO":
                        await context.bot.send_message(chat_id = chat_id, text = "Вы EXCOMMUNICADO. Защита канала вам недоступна")
                    else:
                        await context.bot.send_message(chat_id = chat_id, text = "Канал уже под защитой!")
                    return
            
            admins = await context.bot.get_chat_administrators(chat_id)
            
            if len(admins) == 2:
                info = ""
                for admin in admins:
                    if not admin.user.is_bot:
                        info = f"@{admin.user.username}\n"

                text = (f"Новый запрос на защиту канала:\nВладелец: {info}Канал: {msg.chat.title}\nid: {msg.chat_id}")

                keyboard = ReplyKeyboardMarkup([[f"/protect {msg.chat_id} {msg.chat.title}", "/reject"]], resize_keyboard = True)

                await context.bot.send_message(chat_id = OWNER_ID, text = text, reply_markup = keyboard)

            else:
                await context.bot.send_message(chat_id = chat_id, text = "Регистрация недоступна.\nДля подключения защиты в канале должен быть только один администратор и бот.")
        
        return

    if message_text == "/pig":
        await context.bot.send_message(chat_id = chat_id, text = g.gen(6,10), reply_to_message_id = message_id)
    elif message_text == "/svo":
        await context.bot.send_message(chat_id = chat_id, text = "Данная команда поддерживается только в мессенджере МАКС", reply_to_message_id = message_id)
    else:
        if msg.via_bot == None:
            asyncio.create_task(train_background(message_text))

    if msg.author_signature:
        txt = msg.author_signature
        ok = 0
        if config["owner_names"]:
            for i in config["owner_names"]:
                if i in txt:
                    ok = 1

        if ok:
            if config["uuid"] not in msg.author_signature:
                if (datetime.now() - last_time).total_seconds() > 0.5:
                    await context.bot.delete_message(chat_id = chat_id, message_id = message_id)
                return
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
                    config = load_config()
                    config["mode"] = "Judgment Day"
                    save_config(config)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Системное уведомление «{bot_name}»:\n"
                        "Активирован протокол «Judgment Day».\n"
                        "Все сообщения в канале и чате будут уничтожены.\n"
                        "Доступ пользователей аннулирован.\n"
                        "Попытки обхода бесполезны.\n"
                        "Канал изолирован и находится под полным контролем.\n\n"
                        f"Код подтверждения: {config['Judgment Day Code']}"
                    )

                    await asyncio.sleep(1)
                    name = ""
                    for i in config["protected_users"]:
                        if i["name"] in msg.reply_to_message.author_signature:
                            name = i["name"]
                    for i in range(5,0,-1):
                        config = load_config()
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=(f"{name} EXCOMMUNICADO {i}\n\n"
                                f"Код подтверждения: {config['Judgment Day Code']}"
                            )
                        )
                        await asyncio.sleep(1)
                    config = load_config()
                    for i in config["protected_users"]:
                        if i["name"] in msg.reply_to_message.author_signature:
                                await context.bot.set_chat_title(i["channel_id"], "EXCOMMUNICADO")
                                i["name"] = "74938749037493793409"
                                i["uuid"] = "EXCOMMUNICADO"
                                save_config(config)
                                await context.bot.send_message(
                                    chat_id=chat_id,
                                    text = (
                                        f"{name} EXCOMMUNICADO в силе\n\n"
                                        "Решением системы безопасности Свинья-6 защита вашего канала отозвана.\n\n"
                                        "UUID-подпись аннулирована.\n"
                                        "Канал исключён из списка доверенных и навсегда внесён в черный список.\n\n"
                                        "Вы лишаетесь всех прав и привилегий.\n"
                                        "Отныне вы — изгой.\n\n"
                                        "Доступ к сервисам Свиньи-6 прекращён.\n\n"
                                        "Вердикт окончательный.\n\n"
                                         f"Код подтверждения: {config['Judgment Day Code']}"
                                    ),
                                    reply_to_message_id=msg.reply_to_message.message_id
                                )
                    
                    await asyncio.sleep(1)
                    config = load_config()
                    config["mode"] = "normal"
                    save_config(config)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Системное уведомление «{bot_name}»:\n"
                        "Протокол «Judgment Day» остановлен.\n\n"                
                        f"Код подтверждения: {config['Judgment Day Code']}"
                    )
                    
                new_uuid = str(uuid.uuid4())

                await context.bot.set_chat_title(PERSONAL_CHANNEL_ID, config["owner_name"] + " " + random.randint(0, 0x10FFFF))

                config = load_config()
                config["uuid"] = new_uuid
                save_config(config)
                last_time = datetime.now()
                return
    
    protected = False
    if msg.author_signature:
        for i in config["protected_users"]:
            if i["name"] in msg.author_signature:
                if i["uuid"] not in msg.author_signature:
                    if (datetime.now() - last_time).total_seconds() > 0.5:
                        await context.bot.delete_message(chat_id = chat_id, message_id = message_id)
                    return
                else:
                    protected = True
                    new_uuid = str(uuid.uuid4())

                    await context.bot.set_chat_title(i["channel_id"], i["name"] + " " + random.randint(0, 0x10FFFF))

                    i["uuid"] = new_uuid
                    save_config(config)
                    last_time = datetime.now()

    if msg.animation and msg.animation.file_id in config["bad_gifs"]:
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )
        return

    if msg.author_signature in config["banned_users"]:
        await context.bot.delete_message(chat_id = chat_id, message_id = message_id)
        return

    if config["ban_messages"] == "all":
        await context.bot.delete_message(chat_id = chat_id, message_id = message_id)
        return
    elif config["ban_messages"] == "manual" and check(message_text):
            await context.bot.delete_message(chat_id = chat_id, message_id = message_id)
            return



    if not msg.author_signature:
        if config["anon_enable"] == 0:
            await context.bot.delete_message(chat_id = chat_id, message_id = message_id)
            return


    if msg.author_signature and config["white_lists_mode"] != "off" and not protected:
        ok = False
        if config["white_lists_mode"] == "admins":
            admins = await context.bot.get_chat_administrators(chat_id)
            for u in admins:
                admin = ''
                if u.user.first_name:
                    admin += u.user.first_name
                if u.user.first_name and u.user.last_name:
                    admin += " "
                if u.user.last_name:
                    admin += u.user.last_name

                if admin == msg.author_signature:
                    ok = True

        if config["white_lists_mode"] == "admins" or config["white_lists_mode"] == "manual":
            for u in config["white_list"]:
                if u == msg.author_signature:
                    ok = True

        if not ok:
            await context.bot.delete_message(chat_id = chat_id, message_id = message_id)
            return
    
    if len(messages) >= 10 and messages[-10].age() < 5:
        await tools.blockall(context=context, msg=None, x=0)
        for i in range(-min(40, len(messages)-1), 0):
            if i >= -11 or messages[i].message_text == messages[-1].message_text:
                await context.bot.delete_message(chat_id = chat_id, message_id = messages[i].message_id)

    messages.append(Message(msg.author_signature, message_text, message_id))



async def ban_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    if result.chat.id == PERSONAL_CHANNEL_ID and result.new_chat_member.status == "member":
        user_id = result.new_chat_member.user.id
        await context.bot.ban_chat_member(
            chat_id = result.chat.id,
            user_id = user_id
        )