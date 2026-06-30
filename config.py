import os
import json

TOKEN = ""
JUDGMENT_DAY_TOKEN = ""
OWNER_ID = 0
MAIN_CHANNEL_ID = 0
PERSONAL_CHANNEL_ID = 0
LOGS_CHANNEL_ID = 0
FULL_CHANNEL_ID = 0
ENABLE_TEXT_NOTIFICATIONS = 0
OWNER_NAME = ""

def load_config():
    file_path = "config.json"
    default_data = {        
        "ban_messages": 0,
        "banned": [],
        "banned_users": [],
        "OWNER_NAMEs": [],
        "white_lists_mode" : "off",
        "white_list": [],
        "anon_enable": 0
    }
    
    if not os.path.exists(file_path):
        os.makedirs("configs", exist_ok=True)
        config = default_data.copy()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    global TOKEN, JUDGMENT_DAY_TOKEN, OWNER_ID, MAIN_CHANNEL_ID, PERSONAL_CHANNEL_ID
    global LOGS_CHANNEL_ID, FULL_CHANNEL_ID, ENABLE_TEXT_NOTIFICATIONS, OWNER_NAME

    TOKEN = config["TOKEN"]
    JUDGMENT_DAY_TOKEN = config["JUDGMENT_DAY_TOKEN"]
    OWNER_ID = int(config["OWNER_ID"])
    MAIN_CHANNEL_ID = int(config["MAIN_CHANNEL_ID"])
    PERSONAL_CHANNEL_ID = int(config["PERSONAL_CHANNEL_ID"])
    LOGS_CHANNEL_ID = int(config["LOGS_CHANNEL_ID"])
    FULL_CHANNEL_ID = int(config["FULL_CHANNEL_ID"])
    ENABLE_TEXT_NOTIFICATIONS = int(config["ENABLE_TEXT_NOTIFICATIONS"])
    OWNER_NAME = config["OWNER_NAME"]

    return config

load_config()

def save_config(data):
    file_path = "config.json"
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent = 4)