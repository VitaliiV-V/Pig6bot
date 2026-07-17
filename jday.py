import uuid
from config import *
from settings import *
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler

app = ApplicationBuilder().token(JUDGMENT_DAY_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    config = load_config()
    status = "остановлен"
    if config["mode"] == "Judgment Day":
        status = "активирован"
        
    await msg.reply_text(
        f"Протокол судного дня {status}"
    )

async def delete_all(update, context):
    config = load_config()
    if config["mode"] == "Judgment Day":
        try:
            if  config["Judgment Day Code"] not in update.message.text:
                await update.message.delete()            
        except:
            msg = update.channel_post or update.edited_channel_post
            chat_id = msg.chat_id
            message_id = msg.message_id
            if not msg.text or config["Judgment Day Code"] not in msg.text:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            else:
                config["Judgment Day Code"] = str(uuid.uuid4())
                save_config(config)


app.add_handler(CommandHandler("start", start))    
app.add_handler(MessageHandler(filters.ALL, delete_all))

app.run_polling(allowed_updates=["message", "channel_post", "chat_member"])
