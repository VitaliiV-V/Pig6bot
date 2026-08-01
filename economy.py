import uuid
import tools
import time
import secrets
from config import *
from settings import *
from tools import *
from pathlib import Path
from markovchain import *
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from pig6economy import *
from telegram import (
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


async def replenish_codes(context):
    count = economy.get_active_codes_count()

    if count < 100:
        for _ in range(100 - count):
            economy.create_code(generate_code())


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    args = msg.text.split()
    cnt = 1 if len(args) == 1 else int(args[1])
    q = economy.get_system_codes_count()
    if q < cnt:
        await msg.reply_text(
            text=(
                "❌ <b>Недостаточно кодов</b>\n\n"
                f"Запрошено: <b>{cnt}</b>\n"
                f"Доступно: <b>{q}</b>"
            ),
            parse_mode="HTML",
        )
        return

    config = load_config()
    total = 0
    for _ in range(cnt):
        total += int(config["Pmin"] * (1 + config["constA"] * ((100 - q) / q)))
        q -= 1

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💳 Pay",
                    callback_data=f"pay^{total}${cnt}${user_id}",
                )
            ]
        ]
    )
    await msg.reply_text(
        text=(
            "🧾 <b>Чек сформирован</b>\n\n"
            f"Стоимость: <b>{total} P6T</b>\n\n"
            "Одноразовый код будет отправлен\n"
            "вам в личные сообщения после оплаты.\n\n"
            "После использования код станет недействительным.\n\n"
            "⚠️ Если сообщение будет отклонено системой модерации Свиньи-6, "
            "возврат средств не предусмотрен."
        ),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)

    if not msg or not msg.from_user:
        return

    user_id = msg.from_user.id

    balance = economy.get_balance(user_id)

    codes = economy.get_user_codes(user_id)

    await msg.reply_text(
        text=(
            "💳 <b>Баланс</b>\n\n"
            f"💰 Доступно: <b>{balance} P6T</b>\n\n"
            f"🔑 Кодoв: <b>{len(codes)}</b>"
        ),
        parse_mode="HTML",
    )


async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)

    if not msg or not msg.from_user or not msg.text:
        return

    args = msg.text.split()

    if len(args) != 3:
        if not msg.reply_to_message:
            await msg.reply_text("❌ Формат:\n/pay @username количество")
            return
        else:
            target_username = f"@{msg.reply_to_message.from_user.username}"
            try:
                amount = int(args[1])
            except ValueError:
                await msg.reply_text("❌ Количество должно быть числом.")
                return
    else:
        target_username = args[1]

        try:
            amount = int(args[2])
        except ValueError:
            await msg.reply_text("❌ Количество должно быть числом.")
            return

    config = load_config()

    receiver_id = None
    receiver_name = None

    users = config.get("protected_users", []) + config.get("super_users", [])

    for user in users:
        if user["owner"] == target_username:
            receiver_id = int(user["id"])
            receiver_name = user["owner"]
            break

    if receiver_id is None:
        await msg.reply_text("❌ Пользователь не найден.")
        return

    sender_id = msg.from_user.id

    if amount < 0:
        await msg.reply_text("🖕 Иди нахуй")
        return
    if economy.get_balance(sender_id) < amount:
        await msg.reply_text("❌ Недостаточно средств.")

        return

    if not economy.user_exists(receiver_id):
        economy.add_user(receiver_id)

    success = economy.create_transaction(
        sender_id, receiver_id, amount, "user transfer"
    )

    if not success:
        await msg.reply_text("❌ Не удалось выполнить перевод.")
        return

    await msg.reply_text(
        text=(
            "✅ <b>Перевод выполнен</b>\n\n"
            f"👤 Получатель: <b>{receiver_name}</b>\n"
            f"💰 Сумма: <b>{amount} P6T</b>\n\n"
            "Средства успешно отправлены."
        ),
        parse_mode="HTML",
    )

    try:
        await context.bot.send_message(
            chat_id=receiver_id,
            text=(
                "💳 <b>Новое поступление</b>\n\n"
                f"💰 Вам отправлено: <b>{amount} P6T</b>\n"
                f"👤 От пользователя: <b>@{msg.from_user.username}</b>"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    bot_name = (await context.bot.get_me()).first_name

    if user_id == OWNER_ID:

        args = msg.text.split()

        if len(args) != 3:
            if not msg.reply_to_message:
                await msg.reply_text("Ответьте командой на сообщение")
                return
            else:
                receiver_id = msg.reply_to_message.from_user.id
                receiver_name = f"@{msg.reply_to_message.from_user.username}"
                try:
                    amount = int(args[1])
                except ValueError:
                    await msg.reply_text("❌ Количество должно быть числом.")
                    return

        else:
            try:
                target_username = args[1]
                amount = int(args[2])
                config = load_config()

                receiver_id = None
                receiver_name = None

                users = config.get("protected_users", []) + config.get(
                    "super_users", []
                )

                for user in users:
                    if user["owner"] == target_username:
                        receiver_id = int(user["id"])
                        receiver_name = user["owner"]
                        break

                if receiver_id is None:
                    await msg.reply_text("❌ Пользователь не найден.")
                    return
            except ValueError:
                await msg.reply_text("❌ Количество должно быть числом.")
                return

        if not economy.user_exists(receiver_id):
            economy.add_user(receiver_id)

        success = economy.create_transaction(0, receiver_id, amount, "user transfer")

        if not success:
            await msg.reply_text("❌ Не удалось выполнить перевод.")
            return

        await msg.reply_text(
            text=(
                "✅ <b>Подарок выдан</b>\n\n"
                f"👤 Получатель: <b>{receiver_name}</b>\n"
                f"💰 Сумма: <b>{amount} P6T</b>"
            ),
            parse_mode="HTML",
        )

        try:
            await context.bot.send_message(
                chat_id=receiver_id,
                text=(
                    "💳 <b>Новое поступление</b>\n\n"
                    f"💰 Вам отправлено: <b>{amount} P6T</b>\n"
                    f"👤 От пользователя: SYSTEM"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
    else:
        await msg.reply_text(
            f"Внимание! Системой защиты «{bot_name}»  отражена попытка несанкционированного доступа к телеграм каналу",
            reply_markup=ReplyKeyboardRemove(),
        )


async def xbet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)

    args = msg.text.split()
    chat_id = msg.chat_id
    message_id = msg.message_id
    user_id = msg.from_user.id

    try:
        if args[1] == "all":
            bet = economy.get_balance(user_id)
        else:
            bet = int(args[1])
    except Exception as e:
        await msg.reply_text("❌ Количество должно быть числом.")
        return

    balance = economy.get_balance(user_id)

    if balance < bet:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ <b>Недостаточно P6T</b>\n"
                f"Нужно: <b>{bet} P6T</b>\n"
                f"Доступно: <b>{balance} P6T</b>"
            ),
            parse_mode="HTML",
        )
    else:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⚔️ Accept Bet",
                        callback_data=f"accept_bet^{msg.from_user.id}${msg.from_user.username}${bet}",
                    )
                ]
            ]
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚔️ <b>Вызов на дуэль</b>\n\n"
                f"👤 Инициатор: @{msg.from_user.username}\n"
                f"💰 Ставка: <b>{bet} P6T</b>\n"
                "🪙 Исход: случайный\n\n"
                "После подтверждения победитель определяется\n"
                "подбросом монеты."
            ),
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)


async def accept_bet(query, data):
    p1_id, p1_name, bet = data.split("$")
    p2_id, p2_name = query.from_user.id, query.from_user.username
    p1_id = int(p1_id)
    bet = int(bet)
    p2_id = int(p2_id)

    p1_bal = economy.get_balance(p1_id)
    p2_bal = economy.get_balance(p2_id)
    if p1_bal < bet or p2_bal < bet:
        await query.edit_message_text(
            text=(
                "⚔️ <b>Дуэль отменена</b>\n\n"
                "❌ Недостаточно средств для участия.\n\n"
                f"💰 Требуется ставка: <b>{bet} P6T</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "Пополните баланс и попробуйте снова."
            ),
            parse_mode="HTML",
        )
        return
    winner = secrets.choice([p1_id, p2_id])
    loser = p1_id if winner == p2_id else p2_id
    winner_name = p1_name if winner == p1_id else p2_name
    loser_name = p2_name if loser == p2_id else p1_name

    economy.create_transaction(loser, winner, bet, "game")

    await query.edit_message_text(
        text=(
            "⚔️ <b>Дуэль завершена</b>\n\n"
            f"👤 @{winner_name}\n\n"
            "<b>VS\n\n</b>"
            f"👤 @{loser_name}\n\n"
            "━━━━━━━━━━━━━━\n"
            f"🪙 Победитель: <b>@{winner_name}</b>\n\n"
            f"💰 Выигрыш: <b>{bet * 2} P6T</b>\n"
            "━━━━━━━━━━━━━━"
        ),
        parse_mode="HTML",
    )


async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)
    user_id = msg.from_user.id

    last_salary = economy.get_last_salary(user_id=user_id)

    if last_salary:
        last_salary = datetime.strptime(last_salary, "%Y-%m-%d %H:%M:%S")
    else:
        last_salary = datetime.min

    time_passed = datetime.now() - last_salary

    if time_passed >= timedelta(days=1):
        economy.create_transaction(0, user_id, 100, "salary")

        await msg.reply_text(
            "🎁 Подарок получен!\n\n" "Начислено: <b>+100 P6T</b>",
            parse_mode="HTML",
        )
    else:
        remaining = timedelta(days=1) - time_passed

        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes = remainder // 60

        await msg.reply_text(
            f"⏳ Следующий подарок через " f"<b>{hours}ч {minutes}м</b>.",
            parse_mode="HTML",
        )


async def pr_pay(query, data, context):
    total, cnt, user_id = data.split("$")
    buyer_id = query.from_user.id
    total = int(total)
    cnt = int(cnt)
    user_id = int(user_id)
    balance = int(economy.get_balance(buyer_id))
    count = economy.get_system_codes_count()
    if user_id != buyer_id:
        return
    if balance < total:
        await query.edit_message_text(
            text=(
                "❌ <b>Недостаточно средств</b>\n\n"
                f"Стоимость: <b>{total} P6T</b>\n"
                f"Ваш баланс: <b>{balance} P6T</b>"
            ),
            parse_mode="HTML",
        )
    elif count < cnt:
        await query.edit_message_text(
            text=(
                "❌ <b>Недостаточно кодов</b>\n\n"
                f"Запрошено: <b>{cnt}</b>\n"
                f"Доступно: <b>{count}</b>"
            ),
            parse_mode="HTML",
        )
    else:
        economy.create_transaction(buyer_id, 0, total, "purchase of anonymous codes")
        for _ in range(int(cnt)):
            economy.get_code_for_user(buyer_id)

        codes = economy.get_user_codes(buyer_id)

        codes_text = "".join(
            f"«<code>⠀{code}⠀</code>»,  " for i, code in enumerate(codes, 1)
        )

        codes_text = codes_text[:-3]

        if query.message.chat_id != user_id:
            await query.edit_message_text(
                text=(
                    "✅ <b>Оплата произведена</b>\n\n"
                    f"Количество купленных кодов: <b>{cnt}</b>\n"
                    f"Сумма: <b>{total} P6T</b>\n\n"
                    "Одноразовые коды отправлены Вам в личные сообщения."
                ),
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text(
                text=(
                    "✅ <b>Оплата произведена</b>\n\n"
                    f"Количество купленных кодов: <b>{cnt}</b>\n"
                    f"Сумма: <b>{total} P6T</b>\n\n"
                    f"Одноразовые коды ({len(codes)}):\n\n" + codes_text
                ),
                parse_mode="HTML",
            )

        if query.message.chat_id != user_id:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ <b>Оплата произведена</b>\n\n"
                    f"Количество купленных кодов: <b>{cnt}</b>\n"
                    f"Сумма: <b>{total} P6T</b>\n\n"
                    f"Одноразовые коды ({len(codes)}):\n\n" + codes_text
                ),
                parse_mode="HTML",
            )


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)
    q = economy.get_system_codes_count() + 1
    args = msg.text.split()
    cnt = 1 if len(args) == 1 else int(args[1])
    config = load_config()
    total = 0

    codes = economy.get_user_codes(user_id)

    if len(codes) < cnt:
        await msg.reply_text(
            "❌ <b>У вас нет нужного количества кодов</b>",
            parse_mode="HTML",
        )
        return

    for _ in range(cnt):
        total += int(config["Pmin"] * (1 + config["constA"] * ((100 - q) / q)))
        economy.return_code_to_system(user_id)
        q += 1

    economy.create_transaction(
        0,
        user_id,
        total,
        "sale of anonymous code",
    )

    codes = economy.get_user_codes(user_id)

    codes_text = "".join(
        f"«<code>⠀{code}⠀</code>», " for i, code in enumerate(codes, 1)
    )

    codes_text = codes_text[:-2]

    if codes_text:
        codes_text = f"Ваши оставшиеся коды ({len(codes)}):\n\n" + codes_text
    else:
        codes_text = "Активных кодов больше нет."

    if msg.chat_id != user_id:
        await msg.reply_text(
            text=(
                "✅ <b>Продажа произведена</b>\n\n"
                f"Количество проданных кодов: <b>{cnt}</b>\n"
                f"Сумма: <b>{total} P6T</b>\n\n"
                "Оставшиеся у Вас одноразовые коды отправлены Вам в личные сообщения."
            ),
            parse_mode="HTML",
        )

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "✅ <b>Продажа произведена</b>\n\n"
            f"Количество проданных кодов: <b>{cnt}</b>\n"
            f"Сумма: <b>{total} P6T</b>\n\n"
            "Одноразовые коды:\n\n" + codes_text
        ),
        parse_mode="HTML",
    )


async def codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg or not msg.from_user:
        return
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)
    user_id = msg.from_user.id

    codes = economy.get_user_codes(user_id)

    if not codes:
        await msg.reply_text(
            "🔑 <b>Активных кодов нет</b>",
            parse_mode="HTML",
        )
        return

    codes_text = "".join(
        f"«<code>⠀{code}⠀</code>»,  " for i, code in enumerate(codes, 1)
    )
    codes_text = codes_text[:-3]
    if msg.chat_id == msg.from_user.id:
        await msg.reply_text(
            text=(f"🔑 <b>Ваши активные коды ({len(codes)})</b>\n\n" f"{codes_text}"),
            parse_mode="HTML",
        )


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message

    if not msg or not msg.from_user:
        return
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)
    q = economy.get_system_codes_count()

    config = load_config()

    if q <= 0:
        await msg.reply_text(
            text=("📈 <b>Рынок кодов</b>\n\n" "Кодов на рынке сейчас нет."),
            parse_mode="HTML",
        )
        return

    price = int(config["Pmin"] * (1 + config["constA"] * ((100 - q) / q)))

    await msg.reply_text(
        text=(
            "📈 <b>Рынок кодов</b>\n\n"
            f"Доступно кодов: <b>{q}</b>\n"
            f"Текущая цена: <b>{price} P6T</b>"
        ),
        parse_mode="HTML",
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg or not msg.from_user:
        return
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)
    users = economy.get_top_users(10)

    if not users:
        await msg.reply_text(
            "🏆 <b>Топ пользователей</b>\n\n" "Пока здесь никого нет.",
            parse_mode="HTML",
        )
        return

    lines = ["🏆 <b>Топ пользователей</b>\n"]

    medals = ["🥇", "🥈", "🥉"]

    for i, (name, balance) in enumerate(users, start=1):
        prefix = medals[i - 1] if i <= 3 else f"<b>  {i}. </b>"
        name = name or "Без имени"

        name = name.replace("@", "")
        lines.append(f"{prefix} {name} — <b>{balance} P6T</b>")

    await msg.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
    )
