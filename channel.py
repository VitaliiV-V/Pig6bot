import re
import asyncio
from game import *
from config import *
from censor import *
from settings import *
from markovchain import *
from datetime import datetime
from telegram.ext import ContextTypes
from telegram import Update
from protection import *
from pig6economy import *

g = Generator()


last_time = datetime.now()

superlist = []

for code in range(0xE0100, 0xE01F0):
    superlist.append(chr(code))


async def train_background(text):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, g.train, text)


async def reply_in_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_time, messages
    msg = update.channel_post or update.edited_channel_post

    if not msg:
        return

    chat_id = msg.chat_id
    message_id = msg.message_id
    message_text = msg.text or ""

    config = load_config()
    file = "log.json"

    if os.path.exists(file):
        with open(file, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data[str(message_id)] = get_author_id(msg.author_signature)

    with open(file, "w") as f:
        json.dump(data, f, indent=4)

    if message_text == "/pig":
        await context.bot.send_message(
            chat_id=chat_id, text=g.gen(6, 10), reply_to_message_id=message_id
        )
    elif message_text == "/svo":
        await context.bot.send_message(
            chat_id=chat_id,
            text="Данная команда поддерживается только в мессенджере МАКС",
            reply_to_message_id=message_id,
        )
    elif False and re.fullmatch(r"/bet \d+", message_text):
        bet = int(message_text.replace("/bet ", ""))
        id = get_author_id(msg.author_signature)
        if id == -1:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        else:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=(
                    "⚔️ <b>Вызов на дуэль</b>\n\n"
                    f"👤 Инициатор: {msg.author_signature}\n"
                    f"💰 Ставка: <b>{bet} P6T</b>\n"
                    "🪙 Исход: случайный\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "↩️ Ответьте на это сообщение командой:\n"
                    "<code>/accept</code>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "После подтверждения победитель определяется\n"
                    "подбросом монеты."
                ),
                parse_mode="HTML",
            )
    elif False and message_text == "/accept":
        id = get_author_id(msg.author_signature)
        if id == -1:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        else:
            original_message = msg.reply_to_message

            creator_id = get_author(original_message.message_id)

            match = re.search(r"💰 Ставка:\s*(\d+)\s*P6T", original_message.text)

            bet = int(match.group(1))

            if not match:

                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                return

            winner = secrets.choice(
                [original_message.author_signature, msg.author_signature]
            )

            loser = (
                msg.author_signature
                if winner == original_message.author_signature
                else original_message.author_signature
            )

            economy = Pig6Economy()
            winner_id = (
                get_author_id(winner) if get_author_id(winner) != -1 else creator_id
            )
            loser_id = (
                get_author_id(loser) if get_author_id(loser) != -1 else creator_id
            )

            winner_balance = economy.get_balance(winner_id)
            loser_balance = economy.get_balance(loser_id)

            if winner_balance < bet or loser_balance < bet:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=original_message.message_id,
                    text=(
                        "⚔️ <b>Дуэль отменена</b>\n\n"
                        "❌ Недостаточно средств для участия.\n\n"
                        f"💰 Требуется ставка: <b>{bet} P6T</b>\n"
                        "━━━━━━━━━━━━━━\n"
                        "Пополните баланс и попробуйте снова."
                    ),
                    parse_mode="HTML",
                )
            else:
                economy.create_transaction(loser_id, winner_id, bet, "game")
                economy.close()
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=original_message.message_id,
                    text=(
                        "⚔️ <b>Дуэль завершена</b>\n\n"
                        f"👤 {original_message.author_signature}\n\n"
                        "<b>VS\n\n</b>"
                        f"👤 {msg.author_signature}\n\n"
                        "━━━━━━━━━━━━━━\n"
                        f"🪙 Победитель: <b>{winner}</b>\n\n"
                        f"💰 Выигрыш: <b>{bet * 2} P6T</b>\n"
                        "━━━━━━━━━━━━━━"
                    ),
                    parse_mode="HTML",
                )

            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    else:
        if msg.via_bot == None:
            asyncio.create_task(train_background(message_text))

    if chat_id != MAIN_CHANNEL_ID:
        await protect_query(context=context, msg=msg, config=config)
        return

    if await check_super_user(context=context, msg=msg, config=config):
        return

    if await check_owner(context=context, msg=msg, config=config):
        return

    await check_message(context=context, msg=msg, config=config)

    tools.give_daily_reward()


async def ban_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if not member:
        return

    if (
        member.chat.id == PERSONAL_CHANNEL_ID
        and member.new_chat_member.status == "member"
    ):
        user_id = member.new_chat_member.user.id
        await context.bot.ban_chat_member(chat_id=member.chat.id, user_id=user_id)
