import streamlit as st
import pymongo
import re

# --- CONFIGURATION ---
# In production, we will load this from "Secrets" (Environment Variables)
# For testing locally, paste your connection string here.
MONGO_URI = "mongodb+srv://evansharp_db_user:xyz@clusterduck.asjjrav.mongodb.net/?retryWrites=true&w=majority"

# --- PAGE SETUP ---
st.set_page_config(page_title="Ask Your Mother", page_icon="☕")

# Custom CSS to make it look like your email brand
st.markdown("""
<style>
    .main {max-width: 600px; margin: 0 auto;}
    h1 {text-transform: uppercase; letter-spacing: -1px; text-align: center;}
    .subtitle {text-align: center; color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 2px; margin-top: -15px; margin-bottom: 40px;}
    .stButton button {width: 100%; background-color: #333; color: white; border-radius: 4px;}
    .stButton button:hover {background-color: #555; border-color: #555;}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("Ask Your Mother")
st.markdown('<p class="subtitle">The Weekly Man-ual for Dads (0-5y)</p>', unsafe_allow_html=True)

st.write("""
**Tired of "Mommy Blogs" and generic advice?** Get a curated weekly digest of the best parenting content for dads. 
3 Articles (Read), 1 Podcast (Listen), and 1 Video (Watch). No fluff.
""")

# --- FORM ---
with st.form("signup_form"):
    email = st.text_input("Enter your email address", placeholder="dad@example.com")
    submitted = st.form_submit_button("Subscribe")

    if submitted:
        if email:
            # 1. Validate Email (Simple Regex)
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                st.error("Please enter a valid email address.")
            else:
                # 2. Connect to Mongo
                try:
                    client = pymongo.MongoClient(MONGO_URI)
                    db = client.dad_digest_db
                    subscribers = db.subscribers
                    
                    # 3. Check for duplicates
                    if subscribers.find_one({"email": email}):
                        st.warning("Nice try, buddy! You are already subscribed!")
                    else:
                        # 4. Save to DB
                        subscribers.insert_one({
                            "email": email,
                            "joined_at": "today", # We'll fix date handling later
                            "active": True
                        })
                        st.success("Welcome to the club, big dawg! Check your inbox on Fridays.")
                        st.balloons()
                except Exception as e:
                    st.error(f"Database Error: {e}")
        else:
            st.warning("Please enter an email address.")