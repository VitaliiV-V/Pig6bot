from config import *
from channel import *
from commands import *
from telegram import InputTextMessageContent,InlineQueryResultArticle, Update
from telegram.ext import InlineQueryHandler, ApplicationBuilder, CommandHandler, MessageHandler, filters, ChatMemberHandler

app = ApplicationBuilder().token(TOKEN).build()   

async def pig_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower()

    results = []
    results.append(
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="Pig",
            description="Markov chain generated message",
            input_message_content=InputTextMessageContent(
                f"{g.gen(6,10)}"
            ),
        )
    )

    await update.inline_query.answer(results, cache_time=1)

app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("pig", pig))
app.add_handler(CommandHandler("svo", svo))
app.add_handler(CommandHandler("post", post))
app.add_handler(CommandHandler("jday", jday))
app.add_handler(InlineQueryHandler(pig_query))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("smart", smart))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CommandHandler("reg", register))
app.add_handler(CommandHandler("reject", reject))
app.add_handler(CommandHandler("add", addtolists))
app.add_handler(CommandHandler("setfreq", setfreq))
app.add_handler(CommandHandler("disable", disable))
app.add_handler(CommandHandler("del", delfromlists))
app.add_handler(CommandHandler("blockall", blockall))
app.add_handler(CommandHandler("jdaycode", jdaycode))
app.add_handler(CommandHandler("setwhitelistsmode", setwhitelistsmode))
app.add_handler(MessageHandler(filters.ALL, reply_in_channel))
app.add_handler(ChatMemberHandler(ban_new_members, ChatMemberHandler.CHAT_MEMBER))
app.add_handler(MessageHandler(filters.UpdateType.EDITED_CHANNEL_POST, reply_in_channel))

app.run_polling(allowed_updates=["message", "channel_post", "chat_member", "inline_query"])
