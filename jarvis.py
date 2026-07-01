from settings import *
from config import *
from google import genai

class Jarvis:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.chat = self.client.chats.create(model="gemini-3.1-flash-lite")
        self.config = load_config()
        response = self.chat.send_message(f"Привет! {self.config['base_prompt']}")
        print(response.text)
    def query(self, s):
        self.config = load_config()
        response = self.chat.send_message(f"{s} Не забывай {self.config['base_prompt']}")
        return response.text
