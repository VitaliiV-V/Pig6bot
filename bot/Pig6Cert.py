from telegram import (
    InputTextMessageContent,
    InlineQueryResultArticle,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    MessageEntity,
)
from uuid import uuid4

from config.config import *
from bot.settings import *
import os
import json
import secrets
from datetime import datetime, timezone
from telegram.ext import (
    InlineQueryHandler,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
)

from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

app = ApplicationBuilder().token(CERT_TOKEN).build()

CERT_DIR = "certificates"

os.makedirs(CERT_DIR, exist_ok=True)


async def generate_keypair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    private_dir = "keys/private"
    public_dir = "keys/public"

    os.makedirs(private_dir, exist_ok=True)
    os.makedirs(public_dir, exist_ok=True)

    private_path = os.path.join(private_dir, f"{user_id}.private.pem")

    public_path = os.path.join(public_dir, f"{user_id}.public.pem")

    # если ключи уже есть — не перезаписываем
    if os.path.exists(private_path) or os.path.exists(public_path):
        await update.message.reply_text("⚠️ У вас уже существует ключевая пара.")
        return

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(private_path, "wb") as f:
        f.write(private_bytes)

    with open(public_path, "wb") as f:
        f.write(public_bytes)

    await update.message.reply_text("✅ Ключевая пара создана.\n\n")

    await update.message.reply_document(
        document=open(private_path, "rb"),
        filename=f"{user_id}.private.pem",
        caption=("🔐 Ваш приватный ключ.\n\n" "⚠️ Никому не передавайте этот файл."),
    )

    await update.message.reply_document(
        document=open(public_path, "rb"),
        filename=f"{user_id}.public.pem",
        caption="🔓 Ваш публичный ключ.",
    )


def create_certificate(user, text, signature):

    cert_id = secrets.token_hex(8)

    filename = f"{signature}.json"

    path = os.path.join(CERT_DIR, filename)

    certificate = {
        "id": cert_id,
        "author": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": f"@{user.username}",
        },
        "message": text,
        "signature": signature,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(certificate, f, ensure_ascii=False, indent=4)

    return filename


def sign_message(user_id: int, text: str):

    private_path = f"keys/private/{user_id}.private.pem"

    if not os.path.exists(private_path):

        return None

    with open(private_path, "rb") as f:

        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
        )

    payload = f"{user_id}:{text}".encode("utf-8")

    signature = private_key.sign(payload)

    return signature.hex()


async def post_query(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.inline_query.query
    user_id = update.inline_query.from_user.id

    if not query:
        return

    signature = sign_message(user_id, query)

    if signature is None:

        await update.inline_query.answer(
            [
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="❌ Нет ключа подписи",
                    description="Сначала сгенерируйте ключ через /start",
                    input_message_content=InputTextMessageContent(
                        "❌ У вас нет ключа Pig-6 Certificates.\n\n"
                        "Сначала выполните /start для создания ключей."
                    ),
                )
            ],
            cache_time=0,
            is_personal=True,
        )

        return
    certificate_file = create_certificate(
        update.inline_query.from_user, query, signature
    )
    certificate_file = certificate_file.replace(".json", "")
    certificate_url = f"{WEB_SITE}/certificate/{certificate_file}"

    text = (
        query
        + "\n\n"
        + "This message was signed by Pig-6 Certificates.\nView signature."
    )

    link_text = "View signature"

    entities = [
        MessageEntity(
            type="text_link",
            offset=len(query)
            + 2
            + len("This message was signed by Pig-6 Certificates. "),
            length=len(link_text),
            url=certificate_url,
        )
    ]

    result = InlineQueryResultArticle(
        id=str(uuid4()),
        title="Опубликовать сообщение",
        description="Подписанное Pig-6 Certificate сообщение",
        input_message_content=InputTextMessageContent(
            text,
            entities=entities,
        ),
    )

    await update.inline_query.answer(
        [result],
        cache_time=0,
        is_personal=True,
    )


async def reg(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not context.args:
        await update.message.reply_text("Использование: /reg Название")
        return

    name = " ".join(context.args)

    admin_id = 5149477852

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Принять", callback_data=f"reg_accept:{user.id}:{name}"
            ),
            InlineKeyboardButton(
                "❌ Отклонить", callback_data=f"reg_decline:{user.id}"
            ),
        ]
    ]

    await context.bot.send_message(
        chat_id=admin_id,
        text=(
            "📩 Новый запрос Pig-6 Certificates\n\n"
            f"Имя: {name}\n"
            f"ID: {user.id}\n"
            f"Username: @{user.username}"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await update.message.reply_text("✅ Заявка отправлена")


async def reg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data.split(":")

    action = data[0]
    user_id = data[1]

    if action == "reg_accept":

        name = ":".join(data[2:])

        config = load_config()

        config["signed_users"].append(
            {
                "name": name,
                "owner_id": user_id,
                "owner": f"@{query.from_user.username}",
                "role": "user",
            }
        )

        save_config(config)

        await query.message.reply_text("✅ Пользователь добавлен")
        await context.bot.send_message(
            chat_id=user_id, text="✅ Ваша заявка на Pig-6 Certificates была одобрена."
        )

    elif action == "reg_decline":

        await query.message.reply_text("❌ Заявка отклонена")
        await context.bot.send_message(
            chat_id=user_id, text="❌ Ваша заявка на Pig-6 Certificates была отклонена."
        )


app.add_handler(CommandHandler("reg", reg))
app.add_handler(CallbackQueryHandler(reg_callback))
app.add_handler(CommandHandler("start", generate_keypair))
app.add_handler(InlineQueryHandler(post_query))

app.run_polling(
    allowed_updates=[
        "message",
        "channel_post",
        "chat_member",
        "inline_query",
        "callback_query",
    ]
)
