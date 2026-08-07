import uuid
import bot.tools as tools
import time
import secrets
from config.config import *
from bot.settings import *
from bot.tools import *
from pathlib import Path
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from economy.pig6economy import *
from telegram import (
    ReplyKeyboardRemove,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def check_id(user_id):
    config = load_config()
    if user_id in config["root_users"]:
        return True
    return user_id == OWNER_ID


async def replenish_codes(context):
    count = economy.get_active_codes_count()

    if count < 100:
        for _ in range(100 - count):
            economy.create_code(generate_id())


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message
    user_id = msg.from_user.id
    user_name = msg.from_user.username

    economy.set_name_if_empty(user_id, user_name)
    if not msg or not msg.from_user or not msg.text:
        return

    user_id = msg.from_user.id

    args = msg.text.split()
    if len(args) > 1 and args[1] == "all":
        cnt = 0
        xx = economy.get_system_codes_count()
        balance = economy.get_balance(user_id)
        config2 = load_config()
        while xx > 0 and balance >= int(
            config2["Pmin"] * (1 + config2["constA"] * ((100 - xx) / xx))
        ):
            balance -= int(
                config2["Pmin"] * (1 + config2["constA"] * ((100 - xx) / xx))
            )
            xx -= 1
            cnt += 1
    else:
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
    res = 0
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
            "🧾 <b>Заказ сформирован</b>\n\n"
            f"Запрошено: <b>{cnt}</b>\n"
            f"Стоимость: <b>{total} P6T</b>\n\n"
            "Одноразовые коды будут отправлены\n"
            "вам в личные сообщения после оплаты.\n\n"
            "После использования код станет недействительным.\n\n"
            "⚠️ Если сообщение будет отклонено системой модерации Свиньи-6, "
            "возврат средств не предусмотрен."
        ),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def confirm_pay(query, data, context):
    total, cnt, user_id = data.split("$")
    buyer_id = query.from_user.id
    cnt = int(cnt)
    user_id = int(user_id)
    balance = int(economy.get_balance(buyer_id))
    count = economy.get_system_codes_count()
    if user_id != buyer_id:
        return

    q = economy.get_system_codes_count()

    config = load_config()
    total = 0
    for _ in range(cnt):
        total += int(config["Pmin"] * (1 + config["constA"] * ((100 - q) / q)))
        q -= 1

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
        economy.add_market_history(
            (
                0
                if q == 0
                else int(config["Pmin"] * (1 + config["constA"] * ((100 - q) / q)))
            ),
            q,
        )
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
    if len(args) > 1 and args[1] == "all":
        cnt = len(economy.get_user_codes(user_id))
    else:
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
        total += int(
            (config["Pmin"] * (1 + config["constA"] * ((100 - q) / q)))
            * config["coeff"]
        )
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
    q -= 1
    economy.add_market_history(
        (
            0
            if q == 0
            else int(config["Pmin"] * (1 + config["constA"] * ((100 - q) / q)))
        ),
        q,
    )
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
            f"Продано кодов: <b>{cnt}</b>\n"
            f"Сумма: <b>{total} P6T</b>\n\n"
            "Одноразовые коды:\n\n" + codes_text
        ),
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
            receiver_id = msg.reply_to_message.from_user.id
            receiver_name = f"@{msg.reply_to_message.from_user.username}"
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

    if check_id(user_id):

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
        economy.update_last_salary(user_id)
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
