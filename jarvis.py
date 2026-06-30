from settings import *
from google import genai

class Jarvis:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.chat = self.client.chats.create(model="gemini-3.1-flash-lite")
    def query(self, s):
        response = response = self.chat.send_message(s)
        return response.text

# j = Jarvis()
# message = ""
# condition = "называют ли оскорбляют ли тут как-то человека по имени Тимофей"
# print(j.query(f"Вот текст сообщения : {message}. Определи, {condition}. В качестве ответа пришли вероятность в процентах. Только число и всё."))