import pymongo
import certifi
import toml  # Make sure to install this: pip install toml

# --- CONFIGURATION ---
TARGET_EMAIL = "evan.sharp.303@gmail.com"  # <--- PUT YOUR TEST EMAIL HERE

try:
    # Load secrets from your local file
    secrets = toml.load(".streamlit/secrets.toml")
    MONGO_URI = secrets["MONGO_URI"]
except Exception as e:
    print(f"❌ Could not load secrets: {e}")
    exit()

try:
    # Connect to Database
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client.dad_digest_db
    subscribers = db.subscribers
    
    # 1. DEACTIVATE EVERYONE (The Nuclear Option)
    result_all = subscribers.update_many(
        {}, 
        {"$set": {"active": False}}
    )
    print(f"📉 Deactivated {result_all.modified_count} users.")
    
    # 2. REACTIVATE JUST YOU
    result_me = subscribers.update_one(
        {"email": TARGET_EMAIL},
        {"$set": {"active": True}}
    )
    
    if result_me.modified_count > 0:
        print(f"✅ Reactivated {TARGET_EMAIL}")
    else:
        print(f"⚠️ Warning: Could not find {TARGET_EMAIL} in the database. Are you signed up?")

    # 3. VERIFY
    count = subscribers.count_documents({"active": True})
    print(f"--------------------------------")
    print(f"Total Active Subscribers Now: {count}")
    print(f"--------------------------------")

except Exception as e:
    print(f"Error: {e}")