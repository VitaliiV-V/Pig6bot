import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
JUDGMENT_DAY_TOKEN = os.getenv("JUDGMENT_DAY_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")