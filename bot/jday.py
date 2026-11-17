from config.logging_config import configure_logging

configure_logging()

import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
JUDGMENT_DAY_TOKEN = os.getenv("JUDGMENT_DAY_TOKEN")
LOGS_TOKEN = os.getenv("LOGS_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID"))
MAIN_CHANNEL_ID = int(os.getenv("MAIN_CHANNEL_ID"))
PERSONAL_CHANNEL_ID = int(os.getenv("PERSONAL_CHANNEL_ID"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AI_TOKEN = os.getenv("AI_TOKEN")
CERT_TOKEN = os.getenv("CERT_TOKEN")
OWNER_USERNAME = os.getenv("OWNER_USERNAME")
WEB_SITE = os.getenv("WEB_SITE")


import logging

# from config.config import load_config
# from bot.settings import JUDGMENT_DAY_TOKEN
import os
import json
import logging
import random

logger = logging.getLogger(__name__)


CONFIG_FILE = "config.json"


def load_config():
    default_data = {
        "Pmin": 100,
        "constA": 1,
        "ban_messages": "off",
        "owner_name": "",
        "cost": 300,
        "uuid": "󠄟󠇅󠅸󠇒󠄵",
        "white_lists_mode": "manual",
        "anon_enable": 0,
        "mode": "normal",
        "AI mode": "messages",
        "Judgment Day Code": "",
        "base_prompt": "",
        "banned": [],
        "white_list": [],
        "logs_mode": "off",
        "logs": [],
        "protected_users": [],
        "admins": [],
        "bad_gifs": [],
        "root_users": [],
        "alpha_users": [],
        "signed_users": {},
    }

    try:
        if not os.path.exists(CONFIG_FILE):
            logger.warning(
                "Configuration file '%s' was not found. Creating a new configuration.",
                CONFIG_FILE,
            )

            config = default_data.copy()

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    config,
                    f,
                    ensure_ascii=False,
                    indent=4,
                )

            logger.info(
                "Default configuration created successfully in '%s'.",
                CONFIG_FILE,
            )

            return config

        logger.debug(
            "Loading configuration from '%s'.",
            CONFIG_FILE,
        )

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        logger.info(
            "Configuration loaded successfully from '%s'.",
            CONFIG_FILE,
        )

        return config

    except json.JSONDecodeError:
        logger.exception(
            "Failed to load configuration: invalid JSON in '%s'.",
            CONFIG_FILE,
        )
        raise

    except OSError:
        logger.exception(
            "Failed to access configuration file '%s'.",
            CONFIG_FILE,
        )
        raise

    except Exception:
        logger.exception("Unexpected error while loading configuration.")
        raise


def save_config(data):
    try:
        logger.debug(
            "Saving configuration to '%s'.",
            CONFIG_FILE,
        )

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4,
            )

        logger.info(
            "Configuration saved successfully to '%s'.",
            CONFIG_FILE,
        )

    except TypeError:
        logger.exception("Failed to serialize configuration to JSON.")
        raise

    except OSError:
        logger.exception(
            "Failed to write configuration file '%s'.",
            CONFIG_FILE,
        )
        raise

    except Exception:
        logger.exception("Unexpected error while saving configuration.")
        raise


config = load_config()
for i in config.setdefault("admins", []):
    if not i.get("channel_id"):
        i["channel_id"] = random.randint(1000000000000, 10000000000000 - 1)
save_config(config)

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
