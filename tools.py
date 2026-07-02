from config import *


def ban(s):
    config = load_config()
    if s not in config["banned_users"]:
        config["banned_users"].append(s)
    save_config(config)

def unban(s):
    config = load_config()    
    if s in config["banned_users"]:
        config["banned_users"].remove(s)
    save_config(config)

def setbaseprompt(s):
    config = load_config()
    config["base_prompt"] = s
    save_config(config)