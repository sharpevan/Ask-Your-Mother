import feedparser
import smtplib
import re
import random 
import pymongo
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# --- CONFIGURATION ---
# IMPORTANT: When we push to GitHub, we will remove these keys.
# For now, keep them here to run locally.
GEMINI_API_KEY = "XYZ"
EMAIL_PASSWORD = "ABC"
EMAIL_SENDER = "myemail"

# MONGODB CONNECTION
MONGO_URI = "mongodb+srv://evansharp_db_user:poop@clusterduck.asjjrav.mongodb.net/?retryWrites=true&w=majority"

def get_subscribers():
    """Fetches all active subscribers from MongoDB."""
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client.dad_digest_db
        # Return a list of just the email strings
        users = [u['email'] for u in db.subscribers.find({"active": True})]
        # Always ensure YOU are on the list for testing
        if "evan.sharp.303@gmail.com" not in users:
            users.append("evan.sharp.303@gmail.com")
        return users
    except Exception as e:
        print(f"Error fetching subscribers: {e}")
        return ["evan.sharp.303@gmail.com"] # Fallback

# Replace the hardcoded list with the function call
FRIEND_LIST = get_subscribers()

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
    
    # Mongo Check
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client.dad_digest_db
        archive = db.articles
        mongo_active = True
    except:
        mongo_active = False

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
                            
                            # Deduplication: Skip if link exists in Mongo
                            if mongo_active and archive.find_one({"link": entry.link}):
                                continue
                            
                            content_pool[category].append({
                                'title': entry.title,
                                'link': entry.link,
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

    input_text = "--- READING OPTIONS ---\n"
    for i, a in enumerate(content_pool['read'][:15]):
        input_text += f"READ_{i} | Source: {a['source']} | Title: {a['title']} | Summary: {a['summary']}\n\n"
    
    input_text += "--- LISTENING OPTIONS ---\n"
    for i, a in enumerate(content_pool['listen'][:5]):
        input_text += f"LISTEN_{i} | Source: {a['source']} | Title: {a['title']} | Summary: {a['summary']}\n\n"

    input_text += "--- WATCHING OPTIONS ---\n"
    for i, a in enumerate(content_pool['watch'][:5]):
        input_text += f"WATCH_{i} | Source: {a['source']} | Title: {a['title']} | Summary: {a['summary']}\n\n"

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
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt
    )
    return response.text

# --- NEW: SAVE TO MEMORY ---
def save_sent_articles(html_content):
    """Scans the email we just generated, finds links, and saves to Mongo."""
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client.dad_digest_db
        archive = db.articles
        
        # Regex to find all href="http..." in the email
        links = re.findall(r'href="(http[^"]+)"', html_content)
        
        count = 0
        for link in links:
            # We insert with a unique index on 'link' to prevent dupes
            if not archive.find_one({"link": link}):
                archive.insert_one({
                    "link": link,
                    "sent_at": datetime.now(),
                    "status": "sent"
                })
                count += 1
        print(f"Memory updated: Saved {count} new items to MongoDB.")
    except Exception as e:
        print(f"Memory Error: {e}")

def send_email(content, recipient):
    print(f"Sending to {recipient}...")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = recipient
    msg['Subject'] = f"Ask Your Mother: {datetime.now().strftime('%b %d')}"

    full_html = f"""
    <html>
        <body style="font-family: Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333; padding: 20px;">
            <div style="text-align: center; padding-bottom: 40px;">
                <h1 style="margin: 0; font-size: 32px; letter-spacing: -1px; text-transform: uppercase;">Ask Your Mother</h1>
                <p style="margin: 5px 0 0; color: #666; font-size: 11px; text-transform: uppercase; letter-spacing: 3px;">The Weekly Man-ual</p>
            </div>
            
            {content.replace("```html", "").replace("```", "")}
            
            <div style="text-align: center; font-size: 11px; color: #aaa; padding-top: 50px; margin-top: 50px; border-top: 1px solid #eee;">
                Powered by Python, Gemini, Coffee & Evan Sharp
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
    content = fetch_content()
    if content['read']:
        email_body = ai_curate_content(content)
        if email_body:
            # 1. Send to friends
            for friend in FRIEND_LIST:
                send_email(email_body, friend)
            
            # 2. Save to Memory (NEW)
            save_sent_articles(email_body)
    else:
        print("Not enough content found.")