import os
import toml
import pymongo
import certifi
import google.genai as genai
import smtplib
import feedparser 
import re         
import random
import time     
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# --- UNIVERSAL SECRET LOADER ---
try:
    secrets = toml.load(".streamlit/secrets.toml")
    MONGO_URI = secrets["MONGO_URI"]
    EMAIL_PASSWORD = secrets["EMAIL_PASSWORD"]
    EMAIL_SENDER = secrets["EMAIL_SENDER"]
    # LOGIC UPDATE: We try the new correct name first
    GEMINI_API_KEY = secrets.get("GOOGLE_API_KEY") or secrets.get("GEMINI_API_KEY")
    print("✅ Secrets loaded from local file.")
except Exception as e:
    print(f"⚠️ Could not load local secrets. Checking Environment variables...")
    MONGO_URI = os.getenv("MONGO_URI")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- DIAGNOSTIC CHECK ---
print("DEBUG: Checking Environment Variables...")
print(f"1. MONGO_URI: {'✅ Found' if MONGO_URI else '❌ MISSING'}")
print(f"2. GEMINI_API_KEY Status: {'✅ Found' if GEMINI_API_KEY else '❌ MISSING'}")

if GEMINI_API_KEY:
    print(f"DEBUG: Key Length: {len(GEMINI_API_KEY)}")
    print(f"DEBUG: Key Start: {GEMINI_API_KEY[:4]}...")
    
    # Check for newline safely (Compatible with Python 3.9)
    has_newline = GEMINI_API_KEY.endswith('\n')
    has_space = GEMINI_API_KEY.endswith(' ')
    print(f"DEBUG: Ends with Newline? {'YES' if has_newline else 'NO'}")
    print(f"DEBUG: Ends with Space? {'YES' if has_space else 'NO'}")

# --- CRITICAL SAFETY CHECK ---
if not MONGO_URI or not GEMINI_API_KEY:
    print("❌ FATAL ERROR: One of the required secrets is NULL.")
    exit()

# --- CONFIGURE AI ---
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"❌ AI Client Error: {e}")

# --- SOURCES ---
READ_FEEDS = [
    "https://www.reddit.com/r/daddit/top/.rss?t=week", 
    "https://www.janetlansbury.com/feed/",
    "https://busytoddler.com/feed/",
    "https://www.fatherly.com/feed",
    "https://www.pbs.org/parents/thrive/rss",
    "https://yourparentingmojo.com/feed/",
    "https://www.zerotothree.org/feed/"
]

LISTEN_FEEDS = [
    "https://rss.art19.com/the-daily-dad",           
    "https://feeds.npr.org/510344/podcast.xml"       
]

WATCH_FEEDS = [
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCNepEAWZH0TBu7dkxIbluDw",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCc_-hy0u9-oKlNdMKHBudcQ"
]

def clean_html(raw_html):
    return re.sub('<[^<]+?>', '', raw_html)[:600]

def fetch_content():
    print("Fetching content from the last 30 days...")
    content_pool = {'read': [], 'listen': [], 'watch': []}
    window_start = datetime.now() - timedelta(days=30)
    
    try:
        client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client.dad_digest_db
        archive = db.articles
        client.admin.command('ping')
        mongo_active = True
        print("Connected to MongoDB!")
    except Exception as e:
        mongo_active = False
        print(f"MongoDB unavailable: {e}")

    def process_feeds(feed_list, category):
        for url in feed_list:
            try:
                feed = feedparser.parse(url)
                source_title = feed.feed.get('title', 'Web')
                entries = feed.entries[:10] if "reddit" in url else feed.entries

                for entry in entries:
                    published = entry.get('published_parsed') or entry.get('updated_parsed')
                    if published:
                        dt_published = datetime(*published[:6])
                        if dt_published > window_start:
                            link = entry.get('link', entry.get('guid', ''))
                            if not link: continue
                            if mongo_active and archive.find_one({"link": link}):
                                continue
                            
                            content_pool[category].append({
                                'title': entry.title,
                                'link': link,
                                'summary': clean_html(entry.get('summary', '') or entry.get('title', '')),
                                'source': source_title.upper(),
                                'type': category
                            })
            except Exception as e:
                print(f"Error reading {url}: {e}")

    process_feeds(READ_FEEDS, 'read')
    process_feeds(LISTEN_FEEDS, 'listen')
    process_feeds(WATCH_FEEDS, 'watch')
    return content_pool

def ai_curate_content(content_pool):
    if not content_pool['read']: return None
    
    random.shuffle(content_pool['read'])
    random.shuffle(content_pool['listen'])
    random.shuffle(content_pool['watch'])

    # [DATA PREP]
    input_text = "--- READING OPTIONS ---\n"
    for i, a in enumerate(content_pool['read'][:15]):
        input_text += f"READ_{i} | Source: {a['source']} | Title: {a['title']} | Link: {a['link']} | Summary: {a['summary']}\n\n"
    
    input_text += "--- LISTENING OPTIONS ---\n"
    for i, a in enumerate(content_pool['listen'][:5]):
        input_text += f"LISTEN_{i} | Source: {a['source']} | Title: {a['title']} | Link: {a['link']} | Summary: {a['summary']}\n\n"

    input_text += "--- WATCHING OPTIONS ---\n"
    for i, a in enumerate(content_pool['watch'][:5]):
        input_text += f"WATCH_{i} | Source: {a['source']} | Title: {a['title']} | Link: {a['link']} | Summary: {a['summary']}\n\n"

    prompt = f"""
    You are the editor of "Ask Your Mother," a weekly digest for a dad of children under 5.
    
    TASK:
    Curate the weekly issue by selecting exactly:
    1. **3 Reading Articles** (Max 1 from Reddit).
    2. **1 Podcast Episode** (Listening).
    3. **1 Video** (Watching).

    OUTPUT FORMAT (Strict HTML):
    <div style="margin-bottom: 20px; border-bottom: 2px solid #000; padding-bottom: 5px;">
        <h2 style="font-size: 14px; letter-spacing: 2px; margin: 0;">READING</h2>
    </div>
    [INSERT 3 READING ARTICLES HERE USING THIS CARD FORMAT:]
    <div style="margin-bottom: 30px;">
        <div style="font-size: 11px; color: #888; font-weight: bold; margin-bottom: 5px;">[SOURCE NAME]</div>
        <div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">
            <a href="[LINK]" style="color: #000; text-decoration: none;">[TITLE]</a>
        </div>
        <div style="font-size: 14px; color: #444; line-height: 1.5;">[PUNCHY SUMMARY]</div>
    </div>
    <div style="margin-bottom: 20px; border-bottom: 2px solid #000; padding-bottom: 5px; margin-top: 40px;">
        <h2 style="font-size: 14px; letter-spacing: 2px; margin: 0;">LISTENING</h2>
    </div>
    [INSERT 1 PODCAST HERE]
    <div style="margin-bottom: 20px; border-bottom: 2px solid #000; padding-bottom: 5px; margin-top: 40px;">
        <h2 style="font-size: 14px; letter-spacing: 2px; margin: 0;">WATCHING</h2>
    </div>
    [INSERT 1 VIDEO HERE]
    CONTENT POOL:
    {input_text}
    """
    
    print("Asking Gemini to curate...")
    
    # --- RETRY LOOP ---
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"⚠️ Rate limit hit. Waiting 30 seconds... (Attempt {attempt+1}/3)")
                time.sleep(30)
            else:
                print(f"❌ AI Error: {e}")
                return None
    
    print("❌ Failed after 3 attempts.")
    return None

def save_sent_articles(html_content):
    try:
        client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client.dad_digest_db
        archive = db.articles
        
        # IMPROVED REGEX: Catches single quotes, double quotes, and spaces
        links = re.findall(r'href=["\']\s*(http[^"\']+)\s*["\']', html_content)
        
        count = 0
        skipped = 0
        for link in links:
            # Strip whitespace and tracking params
            clean_link = link.split('?')[0].strip()
            
            # Check if we've seen this clean link before
            if not archive.find_one({"link": {"$regex": f"^{re.escape(clean_link)}"}}) :
                archive.insert_one({
                    "link": clean_link,
                    "original_full_link": link,
                    "sent_at": datetime.now(),
                    "status": "sent"
                })
                count += 1
            else:
                skipped += 1
                
        print(f"Memory updated: Saved {count} new items. (Skipped {skipped} duplicates)")
    except Exception as e:
        print(f"Memory Error: {e}")

def send_email(content, recipient):
    print(f"Sending to {recipient}...")
    clean_body = content.replace("```html", "").replace("```", "")
    unsubscribe_link = f"https://askyourmother.streamlit.app/?unsubscribe={recipient}"
    
    msg = MIMEMultipart()
    msg['From'] = f"The Man-ual for Dads <{EMAIL_SENDER}>"
    msg['To'] = recipient
    msg['Subject'] = f"Ask Your Mother: {datetime.now().strftime('%b %d')}"

    full_html = f"""
    <html>
        <body style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333; padding: 20px;">
            <div style="text-align: center; padding-bottom: 40px;">
                <h1 style="margin: 0; font-size: 32px; letter-spacing: -1px; text-transform: uppercase;">Ask Your Mother</h1>
                <p style="margin: 5px 0 0; color: #666; font-size: 11px; text-transform: uppercase; letter-spacing: 3px;">The Weekly Man-ual</p>
            </div>
            {clean_body}
            <div style="text-align: center; font-size: 11px; color: #aaa; padding-top: 50px; margin-top: 50px; border-top: 1px solid #eee;">
                Powered by Python, Gemini, Coffee & Evan Sharp
                <br><br>
                <p style="font-size: 14px; margin-bottom: 20px;">
                    How was this issue? 
                    <a href="https://askyourmother.streamlit.app/?vote=up" style="text-decoration: none;">👍 Great</a> &nbsp;|&nbsp; 
                    <a href="https://askyourmother.streamlit.app/?vote=down" style="text-decoration: none;">👎 Needs Work</a>
                </p>
                <a href="{unsubscribe_link}" style="color: #aaa; text-decoration: underline;">Unsubscribe</a>
            </div>
        </body>
    </html>
    """
    
    msg.attach(MIMEText(full_html, 'html'))
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
    print("Sent.")

if __name__ == "__main__":
    # --- SMART SAFETY SWITCH ---
    TEST_MODE = True
    # If the YAML says "DIGEST_MODE: LIVE", we turn off test mode.
    # Otherwise, it defaults to Safe Mode (only you).
    if os.getenv("DIGEST_MODE") == "LIVE":
        TEST_MODE = False
    
    print(f"--- STARTING RUN (TEST_MODE: {TEST_MODE}) ---")
    content = fetch_content()
    
    if content['read']:
        email_body = ai_curate_content(content)
        if email_body:
            try:
                client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
                db = client.dad_digest_db
                
                if TEST_MODE:
                    print("🛡️ SAFE MODE: Sending to Admin only.")
                    recipients = [{"email": "evan.sharp.303@gmail.com"}] 
                else:
                    print("🚀 LIVE MODE: Fetching all active subscribers...")
                    recipients = db.subscribers.find({"active": True})
                
                recipient_count = 0
                for user in recipients:
                    target_email = user.get('email')
                    send_email(email_body, target_email)
                    recipient_count += 1
                
                print(f"✅ Process complete. Sent to {recipient_count} dads.")
                if not TEST_MODE:
                    save_sent_articles(email_body)
            except Exception as e:
                print(f"Database Error: {e}")
    else:
        print("Not enough content found.")
