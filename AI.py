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

def check(text, id):

    with open("dict.json", "r", encoding="utf-8") as f:
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

async def query(update, context):
    config = load_config()
    msg = update.message or update.channel_post or update.edited_channel_post
    if not msg:
        return
    chat_id = msg.chat_id
    message_id = msg.message_id
    message_text = msg.text or ""

    isMaster = False
    
    if msg.author_signature:
        txt = msg.author_signature
        ok = 0
        if config["owner_names"]:
            for i in config["owner_names"]:
                if i in txt:
                    ok = 1

        if ok:
            if config["uuid"] not in msg.author_signature:
                return
            isMaster = True
                  

    if not isMaster and msg.author_signature in config["banned_users"]:
        return

    if not isMaster and config["ban_messages"] == "all":
        return
    elif not isMaster and config["ban_messages"] == "manual":
        if check(message_text, chat_id):
            return


        
    if not msg.author_signature:
        if config["anon_enable"] == 0:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return
        
    
    if config["white_lists_mode"] != "off" and (update.channel_post or update.edited_channel_post) and not isMaster:
        ok = False
        if config["white_lists_mode"] == "admins" or config["white_lists_mode"] == "admins_only":
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
            return
    

    x =  context.bot.first_name
    if msg.reply_to_message:
        y = msg.reply_to_message.author_signature
    else:
        y = None
    text = msg.text.lower()
    if (update.message and update.message.from_user.id == OWNER_ID) or "jarvis" in text or "джарвис" in text or (x == y):
        query = text
        query = query.replace('jarvis', '')
        query = query.replace('джарвис', '')
        ans = jarvis.query(f"{query}")
        await context.bot.send_message(chat_id = chat_id, text = ans, reply_to_message_id = message_id)



app.add_handler(CommandHandler("start", start))    
app.add_handler(MessageHandler(filters.ALL, query))

app.run_polling(allowed_updates=["message", "channel_post", "chat_member"])
