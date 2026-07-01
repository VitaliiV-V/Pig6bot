import uuid
from config import *
from settings import *
from jarvis import *
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler

jarvis = Jarvis()

app = ApplicationBuilder().token(AI_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
        
    await msg.reply_text(
        "Привет! Я Свинья-6 AI!"
    )

async def query(update, context):
    msg = update.message or update.channel_post or update.edited_channel_post
    if not msg:
        return
    chat_id = msg.chat_id
    message_id = msg.message_id
    message_text = msg.text or ""

    x =  context.bot.first_name
    if msg.reply_to_message:
        y = msg.reply_to_message.author_signature
    else:
        y = None
    text = msg.text.lower()
    if "jarvis" in text or "джарвис" in text or (x == y):
        query = text
        query = query.replace('jarvis', '')
        query = query.replace('джарвис', '')
        ans = jarvis.query(f"{query}")
        await context.bot.send_message(chat_id = chat_id, text = ans, reply_to_message_id = message_id)


app.add_handler(CommandHandler("start", start))    
app.add_handler(MessageHandler(filters.ALL, query))

app.run_polling(allowed_updates=["message", "channel_post", "chat_member"])
