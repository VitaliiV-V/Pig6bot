import re
import tools
from config import *
from jarvis import *
from settings import *
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
    text2 = msg.text
    if "jarvis" in text or "джарвис" in text or "привет дилдо" in text or (x == y):
        ok = True
        if isMaster:
            ok = False
            text = re.sub(r'[,.!@#$%^&*()_+=?/|]', '', text)
            text = text.split()
            text2 = re.sub(r'[,.!@#$%^&*()_+=?/|]', '', text2)
            text2 = text2.split()
            if text[0] == 'джарвис':
                if text[1] == 'забань' or text[1] == 'бан' or text[1] == 'забанить':
                    if msg.reply_to_message:
                        text2.append(msg.reply_to_message.author_signature)
                    tools.ban(text2[2])
                    await msg.reply_text(
                        f"{text2[2]} заблокирован(-a)"
                    )
                elif text[1] == 'разбань' or text[1] == 'разбан' or text[1] == 'разбанить':
                    if msg.reply_to_message:
                        text2.append(msg.reply_to_message.author_signature)
                    tools.unban(text2[2])
                    await msg.reply_text(
                        f"{text2[2]} разблокирован(-a)"
                    )
                elif text[1] == 'установи' and text[2] == 'базовый' and text[3] == 'промпт':
                    new_prompt = ' '.join(text2[4:])
                    tools.setbaseprompt(new_prompt)
                    jarvis.restart()
                    await msg.reply_text(
                        f"Базовый промпт установлен."
                    )
                elif text[1] == 'покажи' and text[2] == 'базовый' and text[3] == 'промпт':
                    config = load_config()
                    base_prompt = config.get("base_prompt", "Базовый промпт не установлен.")
                    await msg.reply_text(
                        f"Текущий базовый промпт: {base_prompt}"
                    )
                elif text[1] == 'перезагрузка' or text[1] == 'рестарт':
                    jarvis.restart()
                    await msg.reply_text(
                        f"Джарвис перезагружен."
                    )
                elif text[1] == 'включи' and text[2] == 'логи':
                    config = load_config()
                    config["logs_mode"] = "on"
                    save_config(config)
                    await msg.reply_text(
                        f"Логи включены"
                    )
                elif (text[1] == 'выключи' or text[1] == 'отключи') and text[2] == 'логи':
                    config = load_config()
                    config["logs_mode"] = "off"
                    save_config(config)
                    await msg.reply_text(
                        f"Логи выключены."
                    )
                elif text[1] == 'банить' and text[2] == 'все':
                    config = load_config()
                    config["ban_messages"] = "all"
                    save_config(config)
                    await msg.reply_text(
                        f"Все сообщения будут удаляться."
                    )
                elif text[1] == 'банить' and text[2] == 'по' and text[3] == 'фильтру':
                    config = load_config()
                    config["ban_messages"] = "manual"
                    save_config(config)
                    await msg.reply_text(
                        f"Сообщения будут удаляться по фильтру."
                    )
                elif text[1] == 'не' and text[2] == 'банить':
                    config = load_config()
                    config["ban_messages"] = "off"
                    save_config(config)
                    await msg.reply_text(
                        f"Сообщения не будут удаляться."
                    )
                elif text[1] == 'включи' and text[2] == 'анонимные' and text[3] == 'сообщения':
                    config = load_config()
                    config["anon_enable"] = 1
                    save_config(config)
                    await msg.reply_text(
                        f"Анонимные сообщения включены."
                    )
                elif (text[1] == 'выключи' or text[1] == 'отключи') and text[2] == 'анонимные' and text[3] == 'сообщения':
                    config = load_config()
                    config["anon_enable"] = 0
                    save_config(config)
                    await msg.reply_text(
                        f"Анонимные сообщения выключены."
                    )
                elif text[1] == 'судный' and text[2] == 'день':
                    config = load_config()
                    if(config["mode"] == "normal"): 
                        config["mode"] = "Judgment Day" 
                        save_config(config)
                        await msg.reply_text(
                            f"Судный день настал."
                        )
                    else:
                        config["mode"] = "normal" 
                        save_config(config)
                        await msg.reply_text(
                            f"Судный день отменён."
                        )
                elif text[1] == 'добавь' and text[2] == 'в' and text[3] == 'белый' and text[4] == 'список':
                    config = load_config()
                    config["white_list"].append(text2[5])
                    save_config(config)
                    await msg.reply_text(
                        f"{text2[5]} добавлен(-a) в белый список."
                    )
                elif text[1] == 'убери' and text[2] == 'из' and text[3] == 'белого' and text[4] == 'списка':
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
                elif text[1] == 'выключи' and text[2] == 'белый' and text[3] == 'список':
                    config = load_config()
                    config["white_lists_mode"] = "off"
                    save_config(config)
                    await msg.reply_text(   
                        f"Белый список выключён."
                    )
                elif text[1] == 'включи' and text[2] == 'белый' and text[3] == 'список':
                    config = load_config()
                    config["white_lists_mode"] = "admins"
                    save_config(config)
                    await msg.reply_text(
                        f"Белый список включён."
                    )
                elif text[1] == 'работай' and text[2] == 'только' and text[3] == 'в' and text[3] == 'чате':
                    config = load_config()
                    config["AI mode"] = "messages"
                    save_config(config)
                    await msg.reply_text(
                        f"Настройки изменены."
                    )
                elif text[1] == 'работай' and text[2] == 'везде':
                    config = load_config()
                    config["AI mode"] = "all"
                    save_config(config)
                    await msg.reply_text(
                        f"Настройки изменены."
                    )
                else:
                    ok = True
            else:
                ok = True
        if ok:
            query = msg.text.lower()
            query = query.replace('jarvis', '')
            query = query.replace('джарвис', '')
            if isMaster:
                query = f"Это сообщение от {config['owner_name']}: " + query
            else:
                query = f"Это сообщение от {msg.author_signature}: " + query

            ans = jarvis.query(f"{query}")
            if "rejected" not in ans:
                if config["AI mode"] == "all" or (config["AI mode"] == "messages" and update.message):
                    await context.bot.send_message(chat_id = chat_id, text = ans, reply_to_message_id = message_id)



app.add_handler(CommandHandler("start", start))    
app.add_handler(MessageHandler(filters.ALL, query))

app.run_polling(allowed_updates=["message", "channel_post", "chat_member"])
