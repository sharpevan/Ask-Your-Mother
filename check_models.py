import os
import toml
from google import genai

# Load Secrets
try:
    secrets = toml.load(".streamlit/secrets.toml")
    GEMINI_API_KEY = secrets.get("GOOGLE_API_KEY") or secrets.get("GEMINI_API_KEY")
except:
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

print("--- AVAILABLE MODELS ---")
for m in client.models.list():
    if "generateContent" in m.supported_actions:
        print(f"Name: {m.name}")