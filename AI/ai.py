import re
import bot.tools as tools
from config.config import *
from AI.jarvis import *
from bot.settings import *
from time import sleep
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler
from bot.censor import *
from bot.settings import *
from config.config import *
from telegram import Update
from bot.protection import *
from economy.pig6economy import *

jarvis = Jarvis()

app = ApplicationBuilder().token(AI_TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    await msg.reply_text("Привет! Я Свинья-6 AI!")


async def query(update, context):
    msg = update.channel_post or update.edited_channel_post

    message_id = msg.message_id
    x = context.bot.first_name
    if msg.reply_to_message:
        y = msg.reply_to_message.author_signature
    else:
        y = None
    text = msg.text.lower()
    text2 = msg.text
    if (
        "jarvis" in text
        or "джарвис" in text
        or "привет дилдо" in text
        or (x == y)
        or (msg.reply_to_message.from_user.id == context.bot.id)
    ):
        xx = True
        if msg.from_user:
            if msg.from_user.id == 777000:
                xx = False
        if xx:
            ok = True
            if isMaster:
                ok = False
                text = re.sub(r"[,.!@#$%^&*()_+=?/|]", "", text)
                text = text.split()
                text2 = re.sub(r"[,.!@#$%^&*()_+=?/|]", "", text2)
                text2 = text2.split()
                if text[0] == "джарвис":
                    if text[1] == "забань" or text[1] == "бан" or text[1] == "забанить":
                        if msg.reply_to_message:
                            text2.append(msg.reply_to_message.author_signature)
                        tools.ban(text2[2])
                        await msg.reply_text(f"{text2[2]} заблокирован(-a)")
                    elif (
                        text[1] == "разбань"
                        or text[1] == "разбан"
                        or text[1] == "разбанить"
                    ):
                        if msg.reply_to_message:
                            text2.append(msg.reply_to_message.author_signature)
                        tools.unban(text2[2])
                        await msg.reply_text(f"{text2[2]} разблокирован(-a)")
                    elif (
                        text[1] == "установи"
                        and text[2] == "базовый"
                        and text[3] == "промпт"
                    ):
                        new_prompt = " ".join(text2[4:])
                        tools.setbaseprompt(new_prompt)
                        jarvis.restart()
                        await msg.reply_text(f"Базовый промпт установлен.")
                    elif (
                        text[1] == "покажи"
                        and text[2] == "базовый"
                        and text[3] == "промпт"
                    ):
                        config = load_config()
                        base_prompt = config.get(
                            "base_prompt", "Базовый промпт не установлен."
                        )
                        await msg.reply_text(f"Текущий базовый промпт: {base_prompt}")
                    elif text[1] == "перезагрузка" or text[1] == "рестарт":
                        jarvis.restart()
                        await msg.reply_text(f"Джарвис перезагружен.")
                    elif text[1] == "включи" and text[2] == "логи":
                        config = load_config()
                        config["logs_mode"] = "on"
                        save_config(config)
                        await msg.reply_text(f"Логи включены")
                    elif (text[1] == "выключи" or text[1] == "отключи") and text[
                        2
                    ] == "логи":
                        config = load_config()
                        config["logs_mode"] = "off"
                        save_config(config)
                        await msg.reply_text(f"Логи выключены.")
                    elif text[1] == "банить" and text[2] == "все":
                        config = load_config()
                        config["ban_messages"] = "all"
                        save_config(config)
                        await msg.reply_text(f"Все сообщения будут удаляться.")
                    elif (
                        text[1] == "банить" and text[2] == "по" and text[3] == "фильтру"
                    ):
                        config = load_config()
                        config["ban_messages"] = "manual"
                        save_config(config)
                        await msg.reply_text(f"Сообщения будут удаляться по фильтру.")
                    elif text[1] == "не" and text[2] == "банить":
                        config = load_config()
                        config["ban_messages"] = "off"
                        save_config(config)
                        await msg.reply_text(f"Сообщения не будут удаляться.")
                    elif (
                        text[1] == "включи"
                        and text[2] == "анонимные"
                        and text[3] == "сообщения"
                    ):
                        config = load_config()
                        config["anon_enable"] = 1
                        save_config(config)
                        await msg.reply_text(f"Анонимные сообщения включены.")
                    elif (
                        (text[1] == "выключи" or text[1] == "отключи")
                        and text[2] == "анонимные"
                        and text[3] == "сообщения"
                    ):
                        config = load_config()
                        config["anon_enable"] = 0
                        save_config(config)
                        await msg.reply_text(f"Анонимные сообщения выключены.")
                    elif text[1] == "судный" and text[2] == "день":
                        config = load_config()
                        if config["mode"] == "normal":
                            config["mode"] = "Judgment Day"
                            save_config(config)
                            await msg.reply_text(f"Судный день настал.")
                        else:
                            config["mode"] = "normal"
                            save_config(config)
                            await msg.reply_text(f"Судный день отменён.")
                    elif (
                        text[1] == "добавь"
                        and text[2] == "в"
                        and text[3] == "белый"
                        and text[4] == "список"
                    ):
                        config = load_config()
                        config["white_list"].append(text2[5])
                        save_config(config)
                        await msg.reply_text(f"{text2[5]} добавлен(-a) в белый список.")
                    elif (
                        text[1] == "убери"
                        and text[2] == "из"
                        and text[3] == "белого"
                        and text[4] == "списка"
                    ):
                        config = load_config()
                        if text2[5] in config["white_list"]:
                            config["white_list"].remove(text2[5])
                            save_config(config)
                            await msg.reply_text(
                                f"{text2[5]} убран(-a) из белого списка."
                            )
                        else:
                            await msg.reply_text(
                                f"{text2[5]} не найден(-a) в белом списке."
                            )
                    elif (
                        text[1] == "выключи"
                        and text[2] == "белый"
                        and text[3] == "список"
                    ):
                        config = load_config()
                        config["white_lists_mode"] = "off"
                        save_config(config)
                        await msg.reply_text(f"Белый список выключён.")
                    elif (
                        text[1] == "включи"
                        and text[2] == "белый"
                        and text[3] == "список"
                    ):
                        config = load_config()
                        config["white_lists_mode"] = "admins"
                        save_config(config)
                        await msg.reply_text(f"Белый список включён.")
                    elif (
                        text[1] == "включи"
                        and text[2] == "ручной"
                        and text[3] == "список"
                    ):
                        config = load_config()
                        config["white_lists_mode"] = "manual"
                        save_config(config)
                        await msg.reply_text(f"Ручной белый список включён.")
                    elif (
                        text[1] == "работай"
                        and text[2] == "только"
                        and text[3] == "в"
                        and text[4] == "чате"
                    ):
                        config = load_config()
                        config["AI mode"] = "messages"
                        save_config(config)
                        await msg.reply_text(f"Настройки изменены.")
                    elif text[1] == "работай" and text[2] == "везде":
                        config = load_config()
                        config["AI mode"] = "all"
                        save_config(config)
                        await msg.reply_text(f"Настройки изменены.")
                    else:
                        ok = True
                else:
                    ok = True
            if (
                update.message
                and msg.chat_id != -1004485198701
                and chat_id != 5149477852
            ):
                ok = False
            if update.message and msg.from_user.id == chat_id != 5149477852:
                isMaster = True

            if ok:
                sleep(3)
                query = msg.text.lower()
                # query = query.replace('jarvis', '')
                # query = query.replace('джарвис', '')
                if update.message:
                    query = (
                        f"This message written by {msg.from_user.first_name}: " + query
                    )
                else:
                    if isMaster:
                        query = f"ы {config['owner_name']}: " + query
                    else:
                        query = (
                            f"This message written by {msg.author_signature}: " + query
                        )

                ans = jarvis.query(f"{query}")
                if "rejected" not in ans:
                    if config["AI mode"] == "all" or (
                        config["AI mode"] == "messages" and update.message
                    ):
                        await context.bot.send_message(
                            chat_id=chat_id, text=ans, reply_to_message_id=message_id
                        )


app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.ALL, query))

app.run_polling(allowed_updates=["message", "channel_post", "chat_member"])
