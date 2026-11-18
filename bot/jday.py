import logging
from uuid import uuid4

from config.config import load_config, save_config
from bot.settings import JUDGMENT_DAY_TOKEN
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationBuilder,
    ApplicationHandlerStop,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg is None:
        return

    config = load_config()
    status = "остановлен"
    if config["mode"] == "Judgment Day":
        status = "активирован"

    await msg.reply_text(f"Протокол судного дня {status}")


async def delete_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg is None:
        return

    config = load_config()
    if config.get("mode") != "Judgment Day":
        return

    code = config.get("Judgment Day Code", "")
    if code and code in (msg.text or msg.caption or ""):
        config["Judgment Day Code"] = str(uuid4())
        save_config(config)
        raise ApplicationHandlerStop

    try:
        # Delete by ID: text, captions, media and service messages use the same API.
        await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
    except TelegramError as exc:
        logger.warning(
            "Failed to delete Judgment Day message %s in chat %s: %s",
            msg.message_id,
            msg.chat_id,
            exc,
        )

    # Commands must not bypass deletion or produce replies during lockdown.
    raise ApplicationHandlerStop


def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(JUDGMENT_DAY_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, delete_all), group=-1)
    app.add_handler(CommandHandler("start", start, filters=filters.UpdateType.MESSAGE))
    app.run_polling(
        allowed_updates=[
            "message",
            "edited_message",
            "channel_post",
            "edited_channel_post",
        ]
    )


if __name__ == "__main__":
    main()
