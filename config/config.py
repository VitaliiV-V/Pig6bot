import os
import json


def load_config():
    file_path = "config.json"
    default_data = {
        "ban_messages": 0,
        "banned": [],
        "banned_users": [],
        "OWNER_NAMEs": [],
        "white_lists_mode": "off",
        "white_list": [],
        "anon_enable": 0,
    }

    if not os.path.exists(file_path):
        config = default_data.copy()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    return config


load_config()


def save_config(data):
    file_path = "config.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
