from settings import *
from config import *
from google import genai
from google.genai import types


class Jarvis:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.chat = self.client.chats.create(model="gemini-3.1-flash-lite")
        self.config = load_config()
        self.chat = self.client.chats.create(
            model="gemini-3.1-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=self.config["base_prompt"]
            )
        )
    def restart(self):
        self.chat = self.client.chats.create(model="gemini-3.1-flash-lite")
        self.config = load_config()
        self.chat = self.client.chats.create(
            model="gemini-3.1-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=self.config["base_prompt"]
            )
        )
    def query(self, user_query):
        self.config = load_config()
        response = self.chat.send_message(f"{self.config['base_prompt']} {user_query}")
        return response.text
