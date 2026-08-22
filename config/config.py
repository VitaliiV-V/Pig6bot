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
        "banned_users": [],
        "white_list": [],
        "logs_mode": "off",
        "logs": [],
        "protected_users": [],
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
for i in config["admins"]:
    if i.get("channel_id"):
        i["channel_id"] = random.randint(1000000000000, 10000000000000 - 1)
save_config(config)
