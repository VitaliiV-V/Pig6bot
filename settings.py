import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
JUDGMENT_DAY_TOKEN = os.getenv("JUDGMENT_DAY_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID"))
MAIN_CHANNEL_ID = int(os.getenv("MAIN_CHANNEL_ID"))
PERSONAL_CHANNEL_ID = int(os.getenv("PERSONAL_CHANNEL_ID"))
LOGS_CHANNEL_ID = int(os.getenv("LOGS_CHANNEL_ID"))
FULL_CHANNEL_ID = int(os.getenv("FULL_CHANNEL_ID"))
ENABLE_TEXT_NOTIFICATIONS = os.getenv("ENABLE_TEXT_NOTIFICATIONS") == True
OWNER_NAME = os.getenv("OWNER_NAME")