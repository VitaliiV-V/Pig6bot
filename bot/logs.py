import uuid
from config.config import *
from bot.settings import *
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler

app = ApplicationBuilder().token(LOGS_TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    config = load_config()
    if config["logs"].count([msg.from_user.id, f"@{msg.from_user.username}"]) == 0:
        config["logs"].append([msg.from_user.id, f"@{msg.from_user.username}"])
        save_config(config)
        await msg.reply_text(f"Привет, теперь ты будешь получать логи канала)")
    else:
        await msg.reply_text(f"Ты уже получаешь логи канала)")


async def logs(update, context):
    msg = update.channel_post
    config = load_config()
    if config["logs_mode"] == "on":
        for i in config["logs"]:
            await context.bot.forward_message(
                chat_id=i[0], from_chat_id=msg.chat_id, message_id=msg.message_id
            )


app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.ALL, logs))

app.run_polling(allowed_updates=["message", "channel_post", "chat_member"])
