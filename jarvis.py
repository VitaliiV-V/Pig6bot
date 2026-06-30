from settings import *
from google import genai

class Jarvis:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
    def query(self, s):
        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=s
        )
        return response.text

# j = Jarvis()
# message = ""
# condition = "называют ли оскорбляют ли тут как-то человека по имени Тимофей"
# print(j.query(f"Вот текст сообщения : {message}. Определи, {condition}. В качестве ответа пришли вероятность в процентах. Только число и всё."))