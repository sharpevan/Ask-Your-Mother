import os
import google.genai as genai

# Load Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ FATAL: GEMINI_API_KEY is missing from environment.")
    exit(1)

print(f"DEBUG: Key is present. Length: {len(api_key)}")

# Clean the key (Just in case)
clean_key = api_key.strip().replace('"', '').replace("'", "")

try:
    client = genai.Client(api_key=clean_key)
    print("attempting to connect to gemini-flash-latest...")
    
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents="Reply with exactly the word 'Pong'."
    )
    
    print(f"✅ SUCCESS! Gemini Responded: {response.text}")
    
except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")
    exit(1)