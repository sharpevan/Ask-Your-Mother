import streamlit as st
import pymongo
import re
import smtplib
import certifi 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIGURATION ---
try:
    MONGO_URI = st.secrets["MONGO_URI"]
    EMAIL_PASSWORD = st.secrets.get("EMAIL_PASSWORD")
except:
    st.error("Secrets not found. Please check your .streamlit/secrets.toml file.")
    st.stop()

EMAIL_SENDER = "evan.sharp.303@gmail.com"

st.set_page_config(page_title="Ask Your Mother", page_icon="☕")

# --- STYLES ---
st.markdown("""
<style>
    .main {max-width: 600px; margin: 0 auto; font-family: Helvetica;}
    h1 {text-transform: uppercase; letter-spacing: -1px; text-align: center; color: #333;}
    .subtitle {text-align: center; color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 2px; margin-top: -15px; margin-bottom: 40px;}
    .stButton button {width: 100%; background-color: #333; color: white; border-radius: 4px; border: none; padding: 10px;}
    .stButton button:hover {background-color: #555;}
</style>
""", unsafe_allow_html=True)

# --- FUNCTIONS ---
def send_welcome_email(recipient):
    if not EMAIL_PASSWORD: return
    msg = MIMEMultipart()
    msg['From'] = "The Man-ual for Dads <" + EMAIL_SENDER + ">"
    msg['To'] = recipient
    msg['Subject'] = "Welcome! ☕"
    html = """
    <div style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="text-transform: uppercase; letter-spacing: -1px;">You're on the list.</h2>
        <p>Thanks for subscribing to <strong>Ask Your Mother</strong>.</p>
        <p>Every Friday morning, you'll get a curated digest of:</p>
        <ul>
            <li>3 Articles worth reading</li>
            <li>1 Podcast for the commute</li>
            <li>1 Video to watch</li>
        </ul>
        <p>No spam, just the good stuff.</p>
        <p>- Evan</p>
    </div>
    """
    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Welcome email failed: {e}")

def send_admin_notification(new_subscriber):
    if not EMAIL_PASSWORD: return
    msg = MIMEMultipart()
    msg['From'] = "Signup Bot <" + EMAIL_SENDER + ">"
    msg['To'] = EMAIL_SENDER
    msg['Subject'] = f"New Subscriber! 🚀 ({new_subscriber})"
    body = f"Heads up! {new_subscriber} just joined the list."
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Admin notification failed: {e}")

# --- MAIN APP ---
st.title("Ask Your Mother")
st.markdown('<p class="subtitle">The Weekly Man-ual for Dads with Young (0-5) Kids </p>', unsafe_allow_html=True)

st.write("Signup to get a short curated weekly digest for Dads. Each week you'll get: 3 Articles, 1 Podcast, & 1 Video.")

with st.form("signup_form"):
    email = st.text_input("Enter your email address", placeholder="dad@example.com")
    submitted = st.form_submit_button("Subscribe")

    if submitted:
        if email and re.match(r"[^@]+@[^@]+\.[^@]+", email):
            try:
                # --- FINAL CLOUD FIX ---
                # We use certifi.where() which works best on Streamlit Cloud servers
                client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
                
                db = client.dad_digest_db
                subscribers = db.subscribers
                
                if subscribers.find_one({"email": email}):
                    st.warning("You are already on the list!")
                else:
                    subscribers.insert_one({
                        "email": email,
                        "joined_at": datetime.now(),
                        "active": True
                    })
                    send_welcome_email(email)
                    send_admin_notification(email)
                    st.success("Welcome aboard! Check your inbox for a confirmation.")
                    st.balloons()
            except Exception as e:
                st.error(f"Something went wrong: {e}")
        else:
            st.error("Please enter a valid email address.")