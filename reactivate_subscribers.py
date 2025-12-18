import pymongo
import certifi
import toml

# --- CONFIGURATION ---
try:
    secrets = toml.load(".streamlit/secrets.toml")
    MONGO_URI = secrets["MONGO_URI"]
except Exception as e:
    print(f"❌ Could not load secrets: {e}")
    exit()

try:
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client.dad_digest_db
    subscribers = db.subscribers
    
    # --- THE SMART RESTORE ---
    # Logic: "Find everyone who DOES NOT have an 'unsubscribed_at' date 
    # and set them back to Active."
    
    print("Running Smart Restore...")
    
    result = subscribers.update_many(
        { "unsubscribed_at": { "$exists": False } },  # The Filter (Safe people)
        { "$set": { "active": True } }                # The Action (Turn on)
    )
    
    print(f"✅ Reactivated {result.modified_count} subscribers.")
    
    # Verify the counts
    total = subscribers.count_documents({})
    active = subscribers.count_documents({"active": True})
    unsubbed = subscribers.count_documents({"active": False})
    
    print(f"--------------------------------")
    print(f"Total Database Records: {total}")
    print(f"Active Subscribers:     {active}")
    print(f"Inactive (Unsubbed):    {unsubbed}")
    print(f"--------------------------------")

except Exception as e:
    print(f"Error: {e}")