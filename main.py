import logging
from logging.handlers import RotatingFileHandler
import os

os.makedirs("logs", exist_ok=True)

log_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

file_handler = RotatingFileHandler(
    "logs/main.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)

file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("bot").setLevel(logging.INFO)
import logging
from config.config import *
from bot.settings import *
from bot.channel import *
from bot.handlers import *
from olymp.handlers import *
from bot.censor import *
from bot.quote import *
from economy.economy import *
from web.server import *
from bot.protection import *
from logging.handlers import RotatingFileHandler
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("q", quote))
app.add_handler(CommandHandler("quote", quote))
app.add_handler(CommandHandler("top", top_handler))
app.add_handler(CommandHandler("buy", buy_handler))
app.add_handler(CommandHandler("set", set_handler))
app.add_handler(CommandHandler("reg", reg_handler))
app.add_handler(CommandHandler("pay", send_handler))
app.add_handler(CommandHandler("post", post_handler))
app.add_handler(CommandHandler("logs", logs_handler))
app.add_handler(CommandHandler("give", give_handler))
app.add_handler(CommandHandler("sell", sell_handler))
app.add_handler(CommandHandler("jday", jday_handler))
app.add_handler(CallbackQueryHandler(buttons_handler))
app.add_handler(CommandHandler("gift", bonus_handler))
app.add_handler(CommandHandler("d", download_handler))
app.add_handler(CommandHandler("panel", panel_handler))
app.add_handler(CommandHandler("start", start_handler))
app.add_handler(CommandHandler("smart", smart_handler))
app.add_handler(CommandHandler("olymp", olymp_handler))
app.add_handler(CommandHandler("market", market_handler))
app.add_handler(CommandHandler("mycodes", codes_handler))
app.add_handler(CommandHandler("apikey", apikey_handler))
app.add_handler(CommandHandler("config", config_handler))
app.add_handler(CommandHandler("jcode", jdaycode_handler))
app.add_handler(CommandHandler("balance", balance_handler))
app.add_handler(CommandHandler("disable", disable_handler))
app.add_handler(CommandHandler("myaccess", myaccess_handler))
app.add_handler(CommandHandler("download", download_handler))
app.add_handler(CommandHandler("blockall", blockall_handler))
app.add_handler(CommandHandler("gen", generate_codes_handler))
app.add_handler(CommandHandler("reset", delete_codes_handler))
app.add_handler(CommandHandler("setbaseprompt", set_base_prompt_handler))
app.add_handler(MessageHandler(filters.ALL, reply_in_channel))
app.add_handler(
    MessageHandler(filters.UpdateType.EDITED_CHANNEL_POST, reply_in_channel)
)
app.add_handler(
    MessageHandler(
        filters.ChatType.PRIVATE & filters.Document.ALL, receive_config_handler
    )
)


app.job_queue.run_repeating(
    replenish_codes,
    interval=86400,
    first=10,
)

app.run_polling(
    allowed_updates=[
        "message",
        "channel_post",
        "chat_member",
        "inline_query",
        "callback_query",
    ]
)
