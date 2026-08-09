import logging
from config.config import *
from bot.settings import *
from bot.channel import *
from bot.commands import *
from bot.censor import *
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

log_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

file_handler = RotatingFileHandler(
    "logs/main.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

app = ApplicationBuilder().token(TOKEN).build()


app.add_handler(CommandHandler("ban", fban))
app.add_handler(CommandHandler("top", top))
app.add_handler(CommandHandler("buy", buy))
app.add_handler(CommandHandler("pay", send))
app.add_handler(CommandHandler("post", post))
app.add_handler(CommandHandler("logs", logs))
app.add_handler(CommandHandler("give", give))
app.add_handler(CommandHandler("sell", sell))
app.add_handler(CommandHandler("gift", bonus))
app.add_handler(CommandHandler("jday", fjday))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("smart", smart))
app.add_handler(CommandHandler("unban", funban))
app.add_handler(CommandHandler("market", market))
app.add_handler(CommandHandler("mycodes", codes))
app.add_handler(CommandHandler("config", config))
app.add_handler(CommandHandler("jcode", jdaycode))
app.add_handler(CommandHandler("add", addtolists))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("panel", showpanel))
app.add_handler(CommandHandler("disable", fdisable))
app.add_handler(CommandHandler("del", delfromlists))
app.add_handler(CommandHandler("myaccess", myaccess))
app.add_handler(CommandHandler("download", download))
app.add_handler(CallbackQueryHandler(buttons_handler))
app.add_handler(CommandHandler("blockall", blockallh))
app.add_handler(MessageHandler(filters.ALL, reply_in_channel))
app.add_handler(CommandHandler("setbaseprompt", set_base_prompt))
app.add_handler(CommandHandler("setwhitelistsmode", setwhitelistsmode))
app.add_handler(
    MessageHandler(filters.UpdateType.EDITED_CHANNEL_POST, reply_in_channel)
)
app.add_handler(
    MessageHandler(filters.ChatType.PRIVATE & filters.Document.ALL, receive_config)
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
