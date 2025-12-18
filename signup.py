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
    EMAIL_SENDER = st.secrets["EMAIL_SENDER"]
except FileNotFoundError:
    st.error("Secrets not found. Please check your .streamlit/secrets.toml file.")
    st.stop()
except KeyError as e:
    st.error(f"Missing secret: {e}. Please update your secrets.toml or Streamlit Cloud settings.")
    st.stop()

st.set_page_config(page_title="Ask Your Mother", page_icon="☕")

# --- STYLES ---
st.markdown("""
<style>
    .main {max-width: 600px; margin: 0 auto; font-family: Helvetica;}
    h1 {text-transform: uppercase; letter-spacing: -1px; text-align: center; color: #333;}
    .subtitle {text-align: center; color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 2px; margin-top: -15px; margin-bottom: 40px;}
    .stButton button {width: 100%; background-color: #333; color: white; border-radius: 4px; border: none; padding: 10px;}
    .stButton button:hover {background-color: #555;}
    .warning {color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# --- FUNCTIONS ---
def get_db_connection():
    """Centralized DB connection handler"""
    try:
        client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        return client.dad_digest_db
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

def send_welcome_email(recipient):
    if not EMAIL_PASSWORD: return
    
    msg = MIMEMultipart()
    msg['From'] = "The Man-ual for Dads <" + EMAIL_SENDER + ">"
    msg['To'] = recipient
    msg['Subject'] = "Welcome! ☕"
    
    # 1. Define the Unsubscribe Link
    unsubscribe_link = f"https://askyourmother.streamlit.app/?unsubscribe={recipient}"
    
    # 2. Add it to the HTML footer
    html = f"""
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
        <br>
        <hr style="border: 0; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #888;">
            <a href="{unsubscribe_link}" style="color: #888; text-decoration: underline;">Unsubscribe</a>
        </p>
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

# --- MAIN LOGIC ---
st.title("Ask Your Mother")
st.markdown('<p class="subtitle">The Weekly Man-ual for Dads with Young (0-5) Kids </p>', unsafe_allow_html=True)

# 1. Check URL for "?unsubscribe=email"
query_params = st.query_params
unsubscribe_email = query_params.get("unsubscribe")

if unsubscribe_email:
    # --- UNSUBSCRIBE FLOW ---
    st.warning(f"You are about to unsubscribe: **{unsubscribe_email}**")
    st.write("We're sorry to see you go! Click below to confirm.")
    
    if st.button("Confirm Unsubscribe"):
        db = get_db_connection()
        if db is not None:
            result = db.subscribers.update_one(
                {"email": unsubscribe_email},
                {"$set": {"active": False, "unsubscribed_at": datetime.now()}}
            )
            
            if result.modified_count > 0:
                st.success("You have been successfully unsubscribed.")
            elif result.matched_count > 0:
                st.info("You were already unsubscribed.")
            else:
                st.error("Email not found in our records.")
else:
    # --- SIGNUP FLOW (Default) ---
    st.write("Signup to get a short curated weekly digest for Dads. Each week you'll get: 3 Articles, 1 Podcast, & 1 Video.")

    with st.form("signup_form"):
        email = st.text_input("Enter your email address", placeholder="dad@example.com")
        submitted = st.form_submit_button("Subscribe")

        if submitted:
            if email and re.match(r"[^@]+@[^@]+\.[^@]+", email):
                db = get_db_connection()
                subscribers = db.subscribers
                
                existing_user = subscribers.find_one({"email": email})
                
                if existing_user:
                    if existing_user.get('active'):
                        st.warning("You are already on the list!")
                    else:
                        # User was unsubscribed, now coming back!
                        subscribers.update_one(
                            {"email": email},
                            {"$set": {"active": True, "rejoined_at": datetime.now()}}
                        )
                        st.success("Welcome back! You've been reactivated.")
                        send_welcome_email(email)
                else:
                    # Brand new user
                    subscribers.insert_one({
                        "email": email,
                        "joined_at": datetime.now(),
                        "active": True
                    })
                    send_welcome_email(email)
                    send_admin_notification(email)
                    st.success("Welcome aboard! Check your inbox for a confirmation.")
                    st.balloons()
            else:
                st.error("Please enter a valid email address.")