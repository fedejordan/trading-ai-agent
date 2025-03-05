from google import genai
import os

# Cargar variables de entorno desde el archivo .env
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_KEY")
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.0-flash", contents="Explain how AI works"
)
print(response.text)