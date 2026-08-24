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


async def check_id(user_id):
    config = load_config()
    if user_id in config["root_users"]:
        return True
    if user_id == OWNER_ID:
        return True
    return False


async def query(update, context):
    msg = update.message
    chat_id = msg.chat_id
    message_id = msg.message_id
    text = msg.text.lower()
    text2 = msg.text
    if (
        "jarvis" in text
        or "джарвис" in text
        or (msg.reply_to_message.from_user.id == context.bot.id)
    ):
        ok = True
        if await check_id(msg.from_user.id):
            ok = False
            text = re.sub(r"[,.!@#$%^&*()_+=?/|]", "", text)
            text = text.split()
            text2 = re.sub(r"[,.!@#$%^&*()_+=?/|]", "", text2)
            text2 = text2.split()
            if text[0] == "джарвис":
                if (
                    text[1] == "установи"
                    and text[2] == "базовый"
                    and text[3] == "промпт"
                ):
                    new_prompt = " ".join(text2[4:])
                    tools.setbaseprompt(new_prompt)
                    jarvis.restart()
                    await msg.reply_text(f"Базовый промпт установлен.")
                elif (
                    text[1] == "покажи" and text[2] == "базовый" and text[3] == "промпт"
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
                elif text[1] == "банить" and text[2] == "все":
                    config = load_config()
                    config["ban_messages"] = "all"
                    save_config(config)
                    await msg.reply_text(f"Все сообщения будут удаляться.")
                elif text[1] == "банить" and text[2] == "по" and text[3] == "фильтру":
                    config = load_config()
                    config["ban_messages"] = "manual"
                    save_config(config)
                    await msg.reply_text(f"Сообщения будут удаляться по фильтру.")
                elif text[1] == "не" and text[2] == "банить":
                    config = load_config()
                    config["ban_messages"] = "off"
                    save_config(config)
                    await msg.reply_text(f"Сообщения не будут удаляться.")
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
                else:
                    ok = True
            else:
                ok = True

        print(ok)
        if ok:
            sleep(3)
            query = msg.text.lower()
            if update.message:
                query = f"This message written by {msg.from_user.first_name}: " + query
            else:
                query = f"This message written by {msg.author_signature}: " + query

            print(0)
            ans = jarvis.query(f"{query}")
            if "rejected" not in ans:
                await context.bot.send_message(
                    chat_id=chat_id, text=ans, reply_to_message_id=message_id
                )


app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.ALL, query))

app.run_polling(allowed_updates=["message", "channel_post", "chat_member"])
