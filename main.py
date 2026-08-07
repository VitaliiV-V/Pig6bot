from config.config import *
from bot.settings import *
from bot.channel import *
from bot.commands import *
from economy.economy import *
from web.server import *
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

app = ApplicationBuilder().token(TOKEN).build()


app.add_handler(CommandHandler("ban", fban))
app.add_handler(CommandHandler("top", top))
app.add_handler(CommandHandler("buy", buy))
app.add_handler(CommandHandler("pay", send))
app.add_handler(CommandHandler("post", post))
app.add_handler(CommandHandler("jday", fjday))
app.add_handler(CommandHandler("give", give))
app.add_handler(CommandHandler("sell", sell))
app.add_handler(CommandHandler("gift", bonus))
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
