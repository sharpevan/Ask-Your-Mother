import os
import toml
import google.genai as genai

# --- ROBUST SECRET LOADER ---
try:
    # Try loading from local file first
    secrets = toml.load(".streamlit/secrets.toml")
    # check for both potential key names
    GEMINI_API_KEY = secrets.get("GEMINI_API_KEY") or secrets.get("GOOGLE_API_KEY")
    print("✅ Secrets loaded from local file.")
except Exception as e:
    print(f"⚠️ Could not load local secrets. Checking Environment variables...")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# --- CONNECT AND LIST MODELS ---
if not GEMINI_API_KEY:
    print("❌ ERROR: API Key is missing. Check .streamlit/secrets.toml")
else:
    print(f"🔑 Key Found! (Length: {len(GEMINI_API_KEY)})")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("CONNECTING TO GOOGLE...")
        # Just list the first few to prove connection works
        response = client.models.list(config={"page_size": 5}) 
        print("✅ SUCCESS! Connection verified. Here are available models:")
        for m in response:
            print(f" - {m.name}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")