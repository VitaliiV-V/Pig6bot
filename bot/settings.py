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
