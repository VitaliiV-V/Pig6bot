from config.logging_config import configure_logging

configure_logging(log_file="logs/main.log")

import logging
from config.config import *
from bot.settings import *
from bot.channel import *
from bot.handlers import *
from bot.censor import *
from bot.quote import *
from bot.protection import *
from bot.shadow import sub_handler, sub_buttons_handler, author_handler, shop_message_handler, track_private_user, migrate_shadow_channels
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

app = ApplicationBuilder().token(TOKEN).post_init(migrate_shadow_channels).build()

app.add_handler(MessageHandler(filters.ChatType.PRIVATE, track_private_user), group=-3)
app.add_handler(MessageHandler(filters.ALL, shop_message_handler), group=-2)
app.add_handler(CommandHandler("sub", sub_handler, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("q", quote))
app.add_handler(CommandHandler("quote", quote))
app.add_handler(CommandHandler("reg", reg_handler))
app.add_handler(CommandHandler("post", post_handler))
app.add_handler(CommandHandler("link", link_handler))
app.add_handler(CommandHandler("logs", logs_handler))
app.add_handler(CommandHandler("jday", jday_handler))
app.add_handler(CallbackQueryHandler(sub_buttons_handler, pattern=r"^sub\^(change|accept|back)$"))
app.add_handler(CallbackQueryHandler(buttons_handler))
app.add_handler(CommandHandler("d", download_handler))
app.add_handler(CommandHandler("panel", panel_handler))
app.add_handler(CommandHandler("start", start_handler))
app.add_handler(CommandHandler("smart", smart_handler))
app.add_handler(CommandHandler("config", config_handler))
app.add_handler(CommandHandler("jcode", jdaycode_handler))
app.add_handler(CommandHandler("disable", disable_handler))
app.add_handler(CommandHandler("myaccess", myaccess_handler))
app.add_handler(CommandHandler("download", download_handler))
app.add_handler(CommandHandler("blockall", blockall_handler))
app.add_handler(CommandHandler("setbaseprompt", set_base_prompt_handler))
app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, author_handler))
# Process channel posts before CommandHandlers: publishing /commands as Shadow
# must still pass identity and quota checks.
app.add_handler(
    MessageHandler(filters.UpdateType.CHANNEL_POST | filters.UpdateType.EDITED_CHANNEL_POST, channel_post_handler),
    group=-1,
)
app.add_handler(
    MessageHandler(
        filters.ChatType.PRIVATE & filters.Document.ALL, receive_config_handler
    )
)


app.run_polling(
    allowed_updates=[
        "message",
        "channel_post",
        "edited_channel_post",
        "chat_member",
        "callback_query",
    ]
)
