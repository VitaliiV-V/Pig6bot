import uuid
import tools
import asyncio
from config import *
from settings import *
from markovchain import *
from telegram.ext import ContextTypes
from telegram import Update, ReplyKeyboardMarkup

g = Generator()

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

async def train_background(text):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, g.train, text)

async def reply_in_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post or update.edited_channel_post
    if not msg:
        return
    chat_id = msg.chat_id
    message_id = msg.message_id
    message_text = msg.text or ""


    config = load_config()

    if chat_id != MAIN_CHANNEL_ID:
        if "protect" in msg.text.lower():
            for i in config["protected_users"]:
                if i["channel_id"] == msg.chat_id:
                    await context.bot.send_message(chat_id=chat_id, text="Канал уже под защитой!")
                    return
            
            admins = await context.bot.get_chat_administrators(chat_id)
            
            print(len(admins))
            if len(admins) == 2:
                info = ""
                for admin in admins:
                    if not admin.user.is_bot:
                        info = f"@{admin.user.username}\n"
                text = (f"Новый запрос на защиту канала:\n"
                        f"Владелец: {info}"
                        f"Канал: {msg.chat.title}\n"
                        f"id: {msg.chat_id}")

                keyboard = ReplyKeyboardMarkup(
                    [[f"/protect {msg.chat_id} {msg.chat.title}", "/reject"]],
                    resize_keyboard=True
                )

                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text = text,
                    reply_markup=keyboard
                )
            else:
                await context.bot.send_message(chat_id=chat_id, text="Регистрация недоступна.\nДля подключения защиты в канале должен быть только один администратор и бот.")
        
        return

    if message_text == "/pig":
        await context.bot.send_message(chat_id=chat_id, text=g.gen(6,10), reply_to_message_id=message_id)
    elif message_text == "/svo":
        await context.bot.send_message(chat_id=chat_id, text="Данная команда поддерживается только в мессенджере МАКС", reply_to_message_id=message_id)
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
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                return
            else:
                if "/ban" in message_text:
                    tools.ban(msg.reply_to_message.author_signature)
                if "/unban" in message_text:
                    tools.unban(msg.reply_to_message.author_signature)


                new_uuid = str(uuid.uuid4())

                await context.bot.set_chat_title(PERSONAL_CHANNEL_ID, config["owner_name"] + "ㅤㅤㅤㅤㅤㅤ ㅤ ㅤ ㅤ ㅤ ㅤ ㅤ ㅤ " + new_uuid)

                config = load_config()
                config["uuid"] = new_uuid
                save_config(config)

                return
    
    protected = False
    if msg.author_signature:
        for i in config["protected_users"]:
            if i["name"] in msg.author_signature:
                if i["uuid"] not in msg.author_signature:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                    return
                else:
                    protected = True
                    new_uuid = str(uuid.uuid4())

                    await context.bot.set_chat_title(i["channel_id"], i["name"] + "ㅤㅤㅤㅤㅤㅤ ㅤ ㅤ ㅤ ㅤ ㅤ ㅤ ㅤ " + new_uuid)

                    i["uuid"] = new_uuid
                    save_config(config)

    if msg.author_signature in config["banned_users"]:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return

    if config["ban_messages"] == "all":
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return
    elif config["ban_messages"] == "manual":
        if check(message_text, chat_id):
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return



    if not msg.author_signature:
        if config["anon_enable"] == 0:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
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
                print(admin)
                if admin == msg.author_signature:
                    ok = True
        if config["white_lists_mode"] == "admins" or config["white_lists_mode"] == "manual":
            for u in config["white_list"]:
                if u == msg.author_signature:
                    ok = True

        if not ok:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return

    if 0:
        prefix = "⚠️ Unsafe message\n\n"

        entities = msg.entities or []
        for entity in entities:
            entity.offset += len(prefix)

        await context.bot.edit_message_text(
            chat_id=msg.chat_id,
            message_id=msg.message_id,
            text=prefix + msg.text,
            entities=entities
        )
    
    if random.randint(1,config["freq"]) == config["freq"]:
        await context.bot.send_message(chat_id=chat_id, text=g.gen(6,10), reply_to_message_id=message_id)



async def ban_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    if result.chat.id == PERSONAL_CHANNEL_ID and result.new_chat_member.status == "member":
        user_id = result.new_chat_member.user.id
        await context.bot.ban_chat_member(
            chat_id=result.chat.id,
            user_id=user_id
        )