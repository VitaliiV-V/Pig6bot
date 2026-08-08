import logging
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
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    InlineQueryHandler,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = ApplicationBuilder().token(CERT_TOKEN).build()

CERT_DIR = "certificates"

os.makedirs(CERT_DIR, exist_ok=True)


async def generate_keypair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        private_dir = "keys/private"
        public_dir = "keys/public"

        os.makedirs(private_dir, exist_ok=True)
        os.makedirs(public_dir, exist_ok=True)

        private_path = os.path.join(private_dir, f"{user_id}.private.pem")

        public_path = os.path.join(public_dir, f"{user_id}.public.pem")

        # если ключи уже есть — не перезаписываем
        if os.path.exists(private_path) or os.path.exists(public_path):
            logger.info(
                "Keypair generation skipped (already exists) for user_id=%s", user_id
            )
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

        logger.info("Keypair generated for user_id=%s", user_id)

        await update.message.reply_text("✅ Ключевая пара создана.\n\n")

        with open(private_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"{user_id}.private.pem",
                caption=(
                    "🔐 Ваш приватный ключ.\n\n" "⚠️ Никому не передавайте этот файл."
                ),
            )

        with open(public_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"{user_id}.public.pem",
                caption="🔓 Ваш публичный ключ.",
            )

        logger.info("Keypair files delivered to user_id=%s", user_id)
    except Exception:
        # Deliberately not logging key material — only the fact that
        # keypair generation failed for this user.
        logger.exception("generate_keypair() failed for user_id=%s", user_id)
        raise


def get_user_role(user_id: int):
    config = load_config()

    user = config.get("signed_users", {}).get(str(user_id))

    if not user:
        return None

    return user.get("role")


def create_certificate(user, text, signature, shadow=False):
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
        "shadow": shadow,
        "message": text,
        "signature": signature,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(certificate, f, ensure_ascii=False, indent=4)

    logger.info(
        "Certificate created: cert_id=%s author_id=%s shadow=%s file=%s",
        cert_id,
        user.id,
        shadow,
        filename,
    )

    return filename


def sign_message(user_id: int, text: str):
    private_path = f"keys/private/{user_id}.private.pem"

    if not os.path.exists(private_path):
        logger.info("sign_message: no private key for user_id=%s", user_id)
        return None

    with open(private_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
        )

    payload = f"{user_id}:{text}".encode("utf-8")

    signature = private_key.sign(payload)

    # Log that a signature was produced, never the key material or the signature itself.
    logger.info("Message signed by user_id=%s (len=%d chars)", user_id, len(text))

    return signature.hex()


async def post_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query

    user_id = update.inline_query.from_user.id

    if not query:
        return

    try:
        signature = sign_message(user_id, query)

        if signature is None:
            logger.info("Inline post rejected (no key) for user_id=%s", user_id)
            await update.inline_query.answer(
                [
                    InlineQueryResultArticle(
                        id=str(uuid4()),
                        title="❌ Нет ключа подписи",
                        description="Сначала сгенерируйте ключ через /start",
                        input_message_content=InputTextMessageContent(
                            "❌ У вас нет ключа Pig-6 Certificates."
                        ),
                    )
                ],
                cache_time=0,
                is_personal=True,
            )

            return

        role = get_user_role(user_id)

        is_shadow = "shadow" in role

        certificate_file = create_certificate(
            update.inline_query.from_user, query, signature, shadow=is_shadow
        )

        certificate_file = certificate_file.replace(".json", "")

        if is_shadow:
            certificate_url = f"{WEB_SITE}/shadow?signature={certificate_file}"
        else:
            certificate_url = (
                f"{WEB_SITE}/check?signature={certificate_file}&user_id={user_id}"
            )

        text = (
            query
            + "\n\n"
            + "This message was signed by Pig-6 Certificates.\nView signature."
        )

        link_text = "View signature"

        entities = [
            MessageEntity(
                type="text_link",
                offset=(
                    len(query)
                    + 2
                    + len("This message was signed by Pig-6 Certificates. ")
                ),
                length=len(link_text),
                url=certificate_url,
            )
        ]

        result = InlineQueryResultArticle(
            id=str(uuid4()),
            title="Опубликовать сообщение",
            description="Подписанное Pig-6 Certificate сообщение",
            input_message_content=InputTextMessageContent(
                text, entities=entities, disable_web_page_preview=True
            ),
        )

        await update.inline_query.answer(
            [result],
            cache_time=0,
            is_personal=True,
        )
        logger.info(
            "Inline signed post answered for user_id=%s shadow=%s", user_id, is_shadow
        )
    except Exception:
        logger.exception("post_query() failed for user_id=%s", user_id)
        raise


async def reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not context.args:
        await update.message.reply_text("Использование: /reg Название канала")
        return

    name = " ".join(context.args)

    logger.info(
        "Registration request received: user_id=%s username=@%s channel=%r",
        user.id,
        user.username,
        name,
    )

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
    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                "📩 Новый запрос Pig-6 Certificates\n\n"
                f"Канал: {name}\n"
                f"ID пользователя: {user.id}\n"
                f"Username: @{user.username}"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except (BadRequest, Forbidden) as e:
        logger.warning("Failed to notify owner about registration request: %s", e)

    config = load_config()
    for id in config["root_users"]:
        try:
            await context.bot.send_message(
                chat_id=id,
                text=(
                    "📩 Новый запрос Pig-6 Certificates\n\n"
                    f"Канал: {name}\n"
                    f"ID пользователя: {user.id}\n"
                    f"Username: @{user.username}"
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except (BadRequest, Forbidden) as e:
            logger.warning(
                "Failed to notify root user %s about registration request: %s", id, e
            )

    await update.message.reply_text("✅ Заявка отправлена")


async def reg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    data = query.data.split(":")

    action = data[0]
    user_id = data[1]

    try:
        if action == "reg_accept":
            channel_name = ":".join(data[2:])

            config = load_config()

            if "signed_users" not in config:
                config["signed_users"] = {}

            user_id = str(user_id)

            # если пользователя ещё нет
            if user_id not in config["signed_users"]:
                config["signed_users"][user_id] = {
                    "username": f"@{query.from_user.username}",
                    "role": "user",
                    "channels": [channel_name],
                }
                logger.info(
                    "Registration accepted (new signed user): approver=%s target=%s channel=%r",
                    query.from_user.id,
                    user_id,
                    channel_name,
                )
            else:
                # если уже есть - просто добавляем канал
                if "channels" not in config["signed_users"][user_id]:
                    config["signed_users"][user_id]["channels"] = []

                if channel_name not in config["signed_users"][user_id]["channels"]:
                    config["signed_users"][user_id]["channels"].append(channel_name)
                    logger.info(
                        "Registration accepted (channel added): approver=%s target=%s channel=%r",
                        query.from_user.id,
                        user_id,
                        channel_name,
                    )
                else:
                    logger.info(
                        "Registration accepted (channel already present): approver=%s target=%s channel=%r",
                        query.from_user.id,
                        user_id,
                        channel_name,
                    )

            save_config(config)

            await query.message.reply_text(
                "✅ Пользователь добавлен в Pig-6 Certificates"
            )

            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=(
                        "✅ Ваша заявка Pig-6 Certificates была одобрена.\n\n"
                        f"Добавлен канал: {channel_name}"
                    ),
                )
            except (BadRequest, Forbidden) as e:
                logger.warning(
                    "Failed to notify user %s about registration approval: %s",
                    user_id,
                    e,
                )

        elif action == "reg_decline":
            logger.info(
                "Registration declined: approver=%s target=%s",
                query.from_user.id,
                user_id,
            )

            await query.message.reply_text("❌ Заявка отклонена")

            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=("❌ Ваша заявка Pig-6 Certificates была отклонена."),
                )
            except (BadRequest, Forbidden) as e:
                logger.warning(
                    "Failed to notify user %s about registration decline: %s",
                    user_id,
                    e,
                )
    except Exception:
        logger.exception(
            "reg_callback() failed for action=%s user_id=%s", action, user_id
        )
        raise


app.add_handler(CommandHandler("reg", reg))
app.add_handler(CallbackQueryHandler(reg_callback))
app.add_handler(CommandHandler("start", generate_keypair))
app.add_handler(InlineQueryHandler(post_query))

logger.info("Pig-6 Certificates bot starting polling")

app.run_polling(
    allowed_updates=[
        "message",
        "channel_post",
        "chat_member",
        "inline_query",
        "callback_query",
    ]
)
