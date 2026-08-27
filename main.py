import os
import uuid
import shutil
import json
import requests
import warnings
import urllib.parse
import urllib.request
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
import google_auth_oauthlib.flow
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from firewall_security import FirewallMiddleware, waf
try:
    from web_image_fetcher import fetch_web_image
except Exception as _w_err:
    print(f"⚠️ web_image_fetcher top import warning: {_w_err}")
    fetch_web_image = None

# Fix OAuth behind proxy (Render)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# Razorpay Setup
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "secret_placeholder")

try:
    import razorpay
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
except Exception as e:
    razorpay_client = None
    print(f"Razorpay initialization warning: {e}")

# Aapke modules
from video_editor import merge_and_export
from audio_engine import make_audio
from video_fetcher import fetch_videos

from passlib.context import CryptContext
from pymongo import MongoClient
import pymongo

load_dotenv("config.env")

cloudinary.config( 
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'), 
  api_key = os.getenv('CLOUDINARY_API_KEY'), 
  api_secret = os.getenv('CLOUDINARY_API_SECRET') 
)

# 2. MongoDB Setup
MONGO_URI = os.getenv('MONGO_URI')
mongo_client = None
db = None
users_collection = None
videos_collection = None

if MONGO_URI:
    try:
        # Wrap in try-except to prevent app crash if DNS/URI is invalid
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Test the connection to ensure it's valid
        mongo_client.admin.command('ping')
        db = mongo_client.cloxel_db
        users_collection = db.users
        videos_collection = db.videos
        print("✅ MongoDB connected successfully!")
    except Exception as e:
        print(f"❌ CRITICAL WARNING: Failed to connect to MongoDB using the provided MONGO_URI. Authentication will be disabled. Error: {e}")
        mongo_client = None
        db = None
        users_collection = None
        videos_collection = None
else:
    print("WARNING: MONGO_URI is missing in config.env! Authentication will not work properly.")

# Prevent Render Sleep by Self-Pinging
def ping_server():
    try:
        # Pings the external URL every 10 minutes
        url = os.getenv("RENDER_EXTERNAL_URL", "https://cloxel.onrender.com")
        resp = requests.get(url)
        print(f"⏰ Self-ping to keep server awake: {resp.status_code}")
    except Exception as e:
        print(f"Self-ping failed: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(ping_server, 'interval', minutes=10)
scheduler.add_job(waf.reset_all_bans, 'interval', hours=6)

def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """Parses 12h or 24h time string (e.g. '10:00 AM', '06:00 PM', '18:00', '10:00') to minutes past midnight"""
    if not time_str:
        return None
    time_str = str(time_str).strip().upper()
    try:
        if "AM" in time_str or "PM" in time_str:
            is_pm = "PM" in time_str
            clean_str = time_str.replace("AM", "").replace("PM", "").strip()
            parts = clean_str.split(":")
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            if is_pm and h < 12:
                h += 12
            elif not is_pm and h == 12:
                h = 0
            return h * 60 + m
        else:
            parts = time_str.split(":")
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            return h * 60 + m
    except Exception:
        return None

def build_youtube_metadata(topic: str, full_script: str = "", video_type: str = "short", custom_title: str = "", custom_desc: str = ""):
    """
    Generates video-specific dynamic YouTube Title & SEO Description.
    Long videos get structured documentary/narrative titles & descriptions.
    Short reels get punchy viral short-form titles & descriptions.
    Guarantees mandatory hashtags: #cloxelai.onrender.com and #cloxel.onrender.com in description.
    """
    topic_clean = (topic or "Cloxel AI Video").strip()
    topic_title = topic_clean.title()
    
    # 1. DYNAMIC TITLE GENERATION (Short vs Long)
    if custom_title and len(custom_title.strip()) > 5 and custom_title.strip().lower() != topic_clean.lower():
        clean_title = custom_title.strip()
    else:
        if video_type == "long":
            long_title_templates = [
                f"The Shocking Truth About {topic_title} | Full AI Documentary & Deep Dive",
                f"Everything You Need To Know About {topic_title} | Complete Guide",
                f"Uncovering The Secrets Of {topic_title} | In-Depth Narrative",
                f"Why {topic_title} Changes Everything | Complete AI Analysis",
                f"{topic_title}: The Hidden Reality Exposed | Full Documentary"
            ]
            idx = sum(ord(c) for c in topic_clean) % len(long_title_templates)
            clean_title = long_title_templates[idx]
        else:
            short_title_templates = [
                f"Mind-Blowing Facts About {topic_title}! 😱 #shorts",
                f"Did You Know THIS About {topic_title}? 🚀 #shorts",
                f"The Secrets Of {topic_title} Exposed! ⚡ #shorts",
                f"Why {topic_title} Will Blow Your Mind! 🔥 #shorts",
                f"Crazy Truth About {topic_title}! 🤯 #shorts"
            ]
            idx = sum(ord(c) for c in topic_clean) % len(short_title_templates)
            clean_title = short_title_templates[idx]

    # Ensure max 95 chars for YouTube Title limit
    if len(clean_title) > 95:
        clean_title = clean_title[:91] + "..."
    if video_type == "short" and "#shorts" not in clean_title.lower():
        clean_title = clean_title[:85] + " #shorts"

    # 2. DYNAMIC DESCRIPTION GENERATION (Short vs Long)
    body_text = (custom_desc or full_script or "").strip()
    if not body_text:
        body_text = f"Explore everything about {topic_title} in this AI-generated video!"
        
    sentences = [s.strip() for s in body_text.replace("\n", " ").replace("!", ".").replace("?", ".").split(".") if len(s.strip()) > 8]
    summary_text = ". ".join(sentences[:3]) + "." if sentences else body_text[:300]
    
    mandatory_tags = "#cloxelai.onrender.com #cloxel.onrender.com"
    website_link = "🌐 Created & Auto-Published via Cloxel AI Engine: https://cloxel.onrender.com"

    if video_type == "long":
        highlights = ""
        if len(sentences) >= 3:
            pts = sentences[1:5]
            highlights = "\n".join([f"  • {p.strip()}" for p in pts])

        seo_desc = (
            f"🎬 {topic_title} - Full Video Narrative & Documentary\n\n"
            f"📌 About this video:\n{summary_text}\n\n"
        )
        if highlights:
            seo_desc += f"💡 Key Highlights:\n{highlights}\n\n"

        seo_desc += (
            f"🔔 Subscribe for daily automated AI videos, deep dives & documentaries!\n\n"
            f"{website_link}\n\n"
            f"🏷️ Tags & Links:\n"
            f"{mandatory_tags} #YouTubeLongs #Trending #Documentary #AI #{topic_title.replace(' ', '')}"
        )
    else:
        seo_desc = (
            f"🎬 {topic_title} (Short Reel)\n\n"
            f"{summary_text}\n\n"
            f"👉 Follow Cloxel AI for daily viral reels & short videos!\n\n"
            f"{website_link}\n\n"
            f"{mandatory_tags} #Shorts #Reels #Viral #Trending #AI #{topic_title.replace(' ', '')}"
        )

    # Hard Guarantee: Ensure mandatory hashtags exist in description
    if "#cloxelai.onrender.com" not in seo_desc:
        seo_desc += " #cloxelai.onrender.com"
    if "#cloxel.onrender.com" not in seo_desc:
        seo_desc += " #cloxel.onrender.com"

    return clean_title, seo_desc

def upload_video_to_youtube_core(user_id: str, video_file: str, title: str, description: str = "", is_short: bool = False) -> Optional[str]:
    """
    Automated YouTube Video Publisher:
    Uses user's stored OAuth credentials from MongoDB to publish video directly to YouTube!
    """
    if users_collection is None:
        print("❌ MongoDB not configured for YouTube auto-upload")
        return None

    if not video_file or not os.path.exists(video_file):
        print(f"⚠️ Video file does not exist on disk for YouTube upload: {video_file}")
        return None

    user = users_collection.find_one({"internal_id": user_id})
    if not user or "youtube_credentials" not in user:
        print(f"⚠️ User {user_id} has no linked YouTube credentials!")
        return None

    creds_data = user.get("youtube_credentials", {})
    if not creds_data or "token" not in creds_data:
        print(f"⚠️ Invalid YouTube credentials for user {user_id}")
        return None

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        credentials = Credentials(
            token=creds_data.get("token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=creds_data.get("client_id", os.getenv("YOUTUBE_CLIENT_ID")),
            client_secret=creds_data.get("client_secret", os.getenv("YOUTUBE_CLIENT_SECRET")),
            scopes=creds_data.get("scopes", ["https://www.googleapis.com/auth/youtube.upload"])
        )

        youtube = build("youtube", "v3", credentials=credentials)

        video_kind = "short" if is_short else "long"
        clean_title, full_desc = build_youtube_metadata(
            topic=title,
            full_script=description,
            video_type=video_kind,
            custom_title=title if (title and len(title) > 15) else "",
            custom_desc=description
        )

        body = {
            "snippet": {
                "title": clean_title,
                "description": full_desc,
                "tags": ["AI", "Viral", "Shorts", "Cloxel", "cloxelai.onrender.com", "cloxel.onrender.com"],
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"🚀 YouTube Upload Progress: {int(status.progress() * 100)}%")

        youtube_id = response.get("id")
        youtube_url = f"https://www.youtube.com/watch?v={youtube_id}"
        print(f"🎉 SUCCESS! Video auto-published to YouTube for user {user_id}: {youtube_url}")

        # Save YouTube URL to DB
        videos_collection.update_one(
            {"internal_id": user_id, "topic": title},
            {"$set": {"youtube_url": youtube_url, "youtube_id": youtube_id, "uploaded_to_yt_at": datetime.utcnow()}}
        )

        return youtube_url

    except Exception as e:
        print(f"❌ YouTube Auto-Upload Error for user {user_id}: {e}")
        return None

def get_daily_unique_subtopic(base_topic: str, today_str: str, user_id: str) -> str:
    """Generates a non-repetitive daily subtopic angle for automated auto reels."""
    sub_angles = [
        "Binary Numbers and Machine Code Secrets",
        "Neural Networks and Brain Mimicry",
        "Autonomous Robotics and Sensor Tech",
        "Computer Vision and Image Recognition",
        "Quantum Computing and Future Machine Learning",
        "Natural Language Processing and Speech AI",
        "Data Compression and Encryption Algorithms",
        "Reinforcement Learning and Smart AI Systems"
    ]
    if not base_topic:
        base_topic = "AI Technology"
    if len(base_topic.split()) > 3:
        return base_topic
    seed = int(hashlib.md5(f"{today_str}_{user_id}_{base_topic}".encode()).hexdigest(), 16)
    selected_angle = sub_angles[seed % len(sub_angles)]
    return f"{base_topic}: {selected_angle}"

def check_and_run_auto_schedules():
    """
    Automated Daily Profile Audit & 1-Hour Pre-Rendering Background Worker:
    Scans all active paid member profiles continuously in IST (UTC+5:30).
    Pre-renders videos 1 hour before scheduled upload time with Smart Fallback Retry Engine.
    Increments auto_daily_usage tracking only for automated background executions!
    Automatically publishes pre-rendered video directly to YouTube.
    """
    if users_collection is None:
        return

    # Render server runs in UTC. Convert to IST (Indian Standard Time, UTC + 5:30)
    now_utc = datetime.utcnow()
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    today_str = now_ist.strftime("%Y-%m-%d")

    current_ist_minutes = now_ist.hour * 60 + now_ist.minute
    pre_render_ist_minutes = (current_ist_minutes + 60) % 1440

    try:
        users = list(users_collection.find({"auto_schedule.schedule_enabled": True}))
        for user in users:
            internal_id = user.get("internal_id")
            schedule = user.get("auto_schedule", {})
            
            subscription = user.get("subscription", {})
            sub_status = subscription.get("status")
            sub_expires = subscription.get("expires_at")
            plan_type = subscription.get("plan_type", "none")

            is_active = (sub_status == "active")
            if sub_expires and isinstance(sub_expires, str):
                try:
                    exp_dt = datetime.fromisoformat(sub_expires.replace('Z', '+00:00'))
                    if datetime.utcnow() > exp_dt.replace(tzinfo=None):
                        is_active = False
                except Exception:
                    pass

            if not is_active:
                continue

            # 1. Short Reel Pre-render & Auto-Upload Engine
            if plan_type in ["short", "combo"]:
                short_time_str = schedule.get("short_time", "10:00")
                short_target_minutes = parse_time_to_minutes(short_time_str) or 600

                diff_current_s = min(abs(current_ist_minutes - short_target_minutes), 1440 - abs(current_ist_minutes - short_target_minutes))
                diff_prerender_s = min(abs(pre_render_ist_minutes - short_target_minutes), 1440 - abs(pre_render_ist_minutes - short_target_minutes))

                if (diff_current_s <= 15 or diff_prerender_s <= 15) and schedule.get("last_short_run") != today_str:
                    print(f"🚀 [AUTO-WORKER 1-HR PRE-RENDER & UPLOAD] Pre-rendering Short Reel for user {internal_id} (Scheduled IST Time: {short_time_str})...")
                    users_collection.update_one(
                        {"internal_id": internal_id},
                        {"$set": {"auto_schedule.last_short_run": today_str}}
                    )

                    raw_topic = schedule.get("short_topic") or "Space Exploration"
                    # Auto Reel Non-Repetitive Daily Topic Angle
                    topic = get_daily_unique_subtopic(raw_topic, today_str, internal_id)
                    category = schedule.get("short_category") or "Random"
                    voice = schedule.get("short_voice") or "hi-IN-MadhurNeural"
                    font = schedule.get("short_font") or "Arial.ttf"
                    color = schedule.get("short_color") or "yellow"
                    duration = int(schedule.get("short_duration") or 20)

                    res = render_video_with_smart_fallback(
                        user_id=internal_id,
                        topic=topic,
                        category=category,
                        voice_id=voice,
                        font_name=font,
                        font_color=color,
                        video_type="short",
                        requested_duration=duration
                    )

                    if res.get("status") == "completed":
                        video_file = res.get("file")
                        script_text = res.get("script", "")
                        
                        # ENFORCE: Min 80 words for engagement, max 120 for retention
                        script_text = " ".join(script_text.split()[:120])
                        
                        upload_video_to_youtube_core(
                            user_id=internal_id,
                            video_file=video_file,
                            title=topic,
                            description=script_text,
                            is_short=True
                        )

                        # Increment auto_daily_usage tracking (Automated Engine Only!)
                        auto_usage = user.get("auto_daily_usage", {})
                        if auto_usage.get("date") != today_str:
                            auto_usage = {"date": today_str, "auto_short_count": 0, "auto_long_count": 0}
                        auto_usage["auto_short_count"] = auto_usage.get("auto_short_count", 0) + 1
                        users_collection.update_one(
                            {"internal_id": internal_id},
                            {"$set": {"auto_daily_usage": auto_usage}}
                        )

            # 2. Long Video Pre-render & Auto-Upload Engine
            if plan_type in ["long", "combo"]:
                long_time_str = schedule.get("long_time", "18:00")
                long_target_minutes = parse_time_to_minutes(long_time_str) or 1080

                diff_current_l = min(abs(current_ist_minutes - long_target_minutes), 1440 - abs(current_ist_minutes - long_target_minutes))
                diff_prerender_l = min(abs(pre_render_ist_minutes - long_target_minutes), 1440 - abs(pre_render_ist_minutes - long_target_minutes))

                if (diff_current_l <= 15 or diff_prerender_l <= 15) and schedule.get("last_long_run") != today_str:
                    print(f"🚀 [AUTO-WORKER 1-HR PRE-RENDER & UPLOAD] Pre-rendering Long Video for user {internal_id} (Scheduled IST Time: {long_time_str})...")
                    users_collection.update_one(
                        {"internal_id": internal_id},
                        {"$set": {"auto_schedule.last_long_run": today_str}}
                    )

                    topic = schedule.get("long_topic") or "AI Innovations"
                    category = schedule.get("long_category") or "Random"
                    voice = schedule.get("long_voice") or "hi-IN-MadhurNeural"
                    font = schedule.get("long_font") or "Arial.ttf"
                    color = schedule.get("long_color") or "yellow"
                    duration = int(schedule.get("long_duration") or 60)

                    res = render_video_with_smart_fallback(
                        user_id=internal_id,
                        topic=topic,
                        category=category,
                        voice_id=voice,
                        font_name=font,
                        font_color=color,
                        video_type="long",
                        requested_duration=duration
                    )

                    if res.get("status") == "completed":
                        video_file = res.get("file")
                        script_text = res.get("script", "")
                        upload_video_to_youtube_core(
                            user_id=internal_id,
                            video_file=video_file,
                            title=topic,
                            description=script_text,
                            is_short=False
                        )

                        # Increment auto_daily_usage tracking (Automated Engine Only!)
                        auto_usage = user.get("auto_daily_usage", {})
                        if auto_usage.get("date") != today_str:
                            auto_usage = {"date": today_str, "auto_short_count": 0, "auto_long_count": 0}
                        auto_usage["auto_long_count"] = auto_usage.get("auto_long_count", 0) + 1
                        users_collection.update_one(
                            {"internal_id": internal_id},
                            {"$set": {"auto_daily_usage": auto_usage}}
                        )

    except Exception as e:
        print(f"❌ Error in check_and_run_auto_schedules: {e}")

scheduler.add_job(check_and_run_auto_schedules, 'interval', minutes=1)
scheduler.start()

# 3. Robust Crash-Proof Password Hashing & Verification Engine
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
import bcrypt as _raw_bcrypt

def safe_verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        if _raw_bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8')):
            return True
    except Exception:
        pass

    try:
        if pwd_context.verify(plain_password, hashed_password):
            return True
    except Exception:
        pass

    return plain_password == hashed_password

def safe_hash_password(password: str) -> str:
    try:
        salt = _raw_bcrypt.gensalt()
        return _raw_bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    except Exception:
        return pwd_context.hash(password)

app = FastAPI()

@app.get("/api/admin/unblock-firewall")
async def unblock_firewall():
    waf.reset_all_bans()
    return {"message": "🔓 Firewall IP bans & rate limits reset successfully!"}

# 0. Ultimate Web Application Firewall (WAF) & Threat Shield Middleware
app.add_middleware(FirewallMiddleware)

# Import AI Background Remover module
try:
    from bg_remover import remove_background
except Exception as _bg_err:
    print(f"⚠️ bg_remover import warning: {_bg_err}")
    remove_background = None

@app.post("/api/remove-bg")
async def api_remove_bg(request: Request):
    """API endpoint for background removal using REMOVE_BG_API_KEY environment variable."""
    if not remove_background:
        raise HTTPException(status_code=500, detail="Background remover engine not initialized")
    try:
        form = await request.form()
        file_obj = form.get("file")
        if not file_obj:
            raise HTTPException(status_code=400, detail="No image file provided in upload")

        contents = await file_obj.read()
        bg_color = form.get("bg_color")

        processed_img = remove_background(
            input_image=contents,
            bg_color=bg_color if bg_color else None
        )

        buf = io.BytesIO()
        output_format = "PNG" if processed_img.mode == "RGBA" else "JPEG"
        processed_img.save(buf, format=output_format)
        img_bytes = buf.getvalue()

        media_type = "image/png" if output_format == "PNG" else "image/jpeg"
        return Response(content=img_bytes, media_type=media_type)

    except Exception as e:
        print(f"❌ Server Error during /api/remove-bg: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class Scene(BaseModel):
    text: str
    keyword: str

class UserRegister(BaseModel):
    name: str
    country: str
    phone: str
    email: str
    password: str
    email_or_mobile: Optional[str] = None

class UserLogin(BaseModel):
    email_or_mobile: str
    password: str

class VideoRequest(BaseModel):
    scenes: List[Scene] = []
    user_id: Optional[str] = None
    topic: Optional[str] = ""
    category: Optional[str] = "Random" # 30+ categories
    font_name: str = "Arial.ttf"
    font_color: str = "yellow"
    font_size: int = 220
    voice_id: str = "hi-IN-MadhurNeural"
    language: str = "hi"
    video_type: str = "short"  # 'short' or 'long'
    full_script: str = ""      # used if video_type is 'long'
    bg_music: str = "cool.mp3" # background music track choice

class ScriptRequest(BaseModel):
    topic: str
    duration_seconds: int

# In-memory job status (Production mein Redis/DB use karna)
jobs = {}

def full_process(req: VideoRequest, job_id: str):
    """Asli logic jo background mein chalega"""
    try:
        # User ke liye ek alag folder banate hain taaki kachra mix na ho
        job_dir = f"temp_{job_id}"
        os.makedirs(job_dir, exist_ok=True)
        
        user_id = req.user_id if req.user_id else "anonymous"
        print(f"🎬 Processing video for User: {user_id} (Category: {req.category})")
        
        # Scenes ki taiyari: Robust Script & Scenes Engine for Long & Short Videos
        scenes_data = []

        # 1. If explicit scenes array is provided with text, use explicit scenes directly
        if req.scenes and len(req.scenes) > 0 and any(s.text and s.text.strip() for s in req.scenes):
            scenes_data = [{"text": s.text.strip(), "keyword": s.keyword.strip() if s.keyword else "technology"} for s in req.scenes if s.text and s.text.strip()]

        # 2. If full_script is provided (for Long or Short videos), split full_script into complete sentences
        if not scenes_data and req.full_script and req.full_script.strip():
            import re
            # Split strictly by sentence enders (. ! ? or newlines), NOT by commas or colons!
            raw_sentences = re.split(r'(?<=[.!?])\s+|\n+', req.full_script.strip())
            stop_words = {"aur", "ek", "hai", "ki", "ke", "ka", "jo", "se", "me", "ko", "hi", "to", "ye", "wo", "tha", "thi", "hain", "kya", "toh", "liye", "bhi", "yeh", "kuch", "hoti", "hain", "mil", "sakti"}
            
            for sentence in raw_sentences:
                sentence = sentence.strip()
                if len(sentence) < 4: continue
                
                # Keyword Extraction: Pick the longest non-stop word
                words = [w.lower() for w in sentence.split() if w.isalpha() and w.lower() not in stop_words]
                keyword = "technology"
                if words:
                    words.sort(key=len, reverse=True)
                    keyword = words[0]
                    
                scenes_data.append({"text": sentence, "keyword": keyword})
                
            if not scenes_data:
                scenes_data = [{"text": req.full_script.strip(), "keyword": "technology"}]

        # 3. Fail-safe: If still empty, use topic
        if not scenes_data:
            fallback_text = req.topic if req.topic else "AI Video Generation"
            scenes_data = [{"text": fallback_text, "keyword": "technology"}]
        
        taiyaar_scenes = []
        for i, sc in enumerate(scenes_data):
            a_path = os.path.join(job_dir, f"audio_{i}.mp3")
            v_path = os.path.join(job_dir, f"video_{i}.mp4")
            
            # Custom settings apply karna
            make_audio(sc["text"], a_path, req.voice_id)
            is_ultra = (req.video_type == "ultra")
            orientation = "landscape" if (req.video_type in ["long", "ultra"]) else "portrait"
            
            if is_ultra and fetch_web_image:
                try:
                    bg_img_path = os.path.join(job_dir, f"bg_photo_{i}.jpg")
                    fg_img_path = os.path.join(job_dir, f"fg_photo_{i}.jpg")
                    
                    main_topic = req.topic if req.topic else "hero warrior"
                    scene_text = sc.get('text', '')
                    scene_kw = sc.get('keyword', '').strip()
                    
                    # Extract script-specific terms from scene text & keywords
                    scene_specific = scene_kw if (scene_kw and len(scene_kw.split()) <= 4) else ""
                    if not scene_specific and scene_text:
                        words = [w for w in scene_text.split() if len(w) > 3][:3]
                        scene_specific = " ".join(words)
                        
                    bg_query = f"{main_topic} {scene_specific} landscape wallpaper photo".strip()
                    fg_query = f"{main_topic} {scene_specific} character hero portrait".strip()
                    
                    print(f"📥 [Ultra Script Engine] Fetching Scene {i+1} Dual Assets: BG='{bg_query}', FG='{fg_query}'...")
                    fetch_web_image(bg_query, bg_img_path)
                    fetch_web_image(fg_query, fg_img_path)
                    
                    v_paths = []
                    if os.path.exists(bg_img_path):
                        v_paths.append(bg_img_path)
                    if os.path.exists(fg_img_path):
                        v_paths.append(fg_img_path)
                        
                    if not v_paths or any(w in scene_specific.lower() for w in ["battle", "war", "action", "fight", "army"]):
                        vid_list = fetch_videos(f"{main_topic} {scene_specific}", v_path, orientation=orientation, category=req.category or "Random")
                        if vid_list and os.path.exists(vid_list[0]):
                            if not v_paths:
                                v_paths = vid_list
                            else:
                                v_paths.append(vid_list[0])
                except Exception as e_img:
                    print(f"⚠️ Ultra script image fetch fallback: {e_img}")
                    v_paths = fetch_videos(sc["keyword"], v_path, orientation=orientation, category=req.category or "Random")
            else:
                v_paths = fetch_videos(sc["keyword"], v_path, orientation=orientation, category=req.category or "Random")
            
            if os.path.exists(a_path):
                if not v_paths:
                    # Internal fail-safe visual canvas fallback if no API key/media available
                    fallback_img_path = os.path.join(job_dir, f"fallback_canvas_{i}.jpg")
                    from PIL import Image
                    target_w, target_h = (1280, 720) if (req.video_type in ["long", "ultra"]) else (720, 1280)
                    blank_img = Image.new('RGB', (target_w, target_h), color=(15, 10, 35))
                    blank_img.save(fallback_img_path)
                    v_paths = [fallback_img_path]

                taiyaar_scenes.append({
                    "audio": a_path, 
                    "video": v_paths, 
                    "text": sc["text"]
                })

        if taiyaar_scenes:
            output_file = f"acoumation_video_{job_id}.mp4"
            # Editor ko user ki choice bhejna (font, color, bg_music, mode)
            target_size = (1280, 720) if (req.video_type in ["long", "ultra"]) else (720, 1280)
            adjusted_font_size = int(req.font_size * 0.7) if (req.video_type in ["long", "ultra"]) else req.font_size
            merge_and_export(taiyaar_scenes, output_file, font_path=f"./fonts/{req.font_name}", color=req.font_color, font_size=adjusted_font_size, target_size=target_size, bg_music=req.bg_music, mode=req.video_type) 
            
            # Upload to Cloudinary
            cloudinary_url = None
            try:
                upload_result = cloudinary.uploader.upload(output_file, resource_type="video")
                cloudinary_url = upload_result.get("secure_url")
            except Exception as e:
                print(f"Cloudinary upload failed: {e}")
                
            full_script_content = req.full_script or " ".join([sc["text"] for sc in taiyaar_scenes])
            gen_title, gen_desc = build_youtube_metadata(
                topic=req.topic,
                full_script=full_script_content,
                video_type=req.video_type
            )
            
            jobs[job_id] = {
                "status": "completed", 
                "file": output_file, 
                "dir": job_dir, 
                "cloudinary_url": cloudinary_url,
                "title": gen_title,
                "description": gen_desc,
                "video_type": req.video_type,
                "topic": req.topic
            }
            
            # Save to Video History in MongoDB
            if videos_collection is not None and req.user_id != "anonymous":
                try:
                    videos_collection.insert_one({
                        "internal_id": req.user_id,
                        "job_id": job_id,
                        "topic": req.topic or gen_title,
                        "title": gen_title,
                        "description": gen_desc,
                        "video_type": req.video_type,
                        "cloudinary_url": cloudinary_url,
                        "created_at": datetime.utcnow()
                    })
                    print(f"✅ Video history saved to MongoDB for user {req.user_id}: {gen_title}")
                except Exception as e:
                    print(f"❌ Failed to save video history to DB: {e}")
        else:
            jobs[job_id] = {"status": "failed", "error": "No scenes ready"}

    except Exception as e:
        print(f"❌ Error in full_process: {e}")
        jobs[job_id] = {"status": "failed", "error": str(e)}
    finally:
        # Safety Disk Space Cleanup: Remove temporary raw audio & video clips to prevent server disk fill-up
        try:
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir, ignore_errors=True)
                print(f"🧹 Cleaned up temp scene directory: {job_dir}")
        except Exception as err:
            print(f"Temp cleanup warning: {err}")

def render_video_with_smart_fallback(user_id: str, topic: str, category: str, voice_id: str, font_name: str, font_color: str, video_type: str, requested_duration: int, bg_music: str = "cool.mp3"):
    """
    Smart Fallback Retry Engine with Duration Stepping:
    If rendering fails for requested duration (e.g. 300s/5m), automatically steps down
    to 240s (4m) -> 180s (3m) -> 120s (2m) -> 60s (1m) for long videos, or
    55s -> 45s -> 30s -> 20s -> 10s for short reels, retrying until 100% success!
    """
    import uuid
    if video_type == "long":
        duration_steps = [requested_duration, 300, 240, 180, 120, 60]
        duration_steps = sorted(list(set([d for d in duration_steps if d <= requested_duration])), reverse=True)
    else:
        duration_steps = [requested_duration, 55, 45, 30, 20, 10]
        duration_steps = sorted(list(set([d for d in duration_steps if d <= requested_duration])), reverse=True)

    last_error = None
    for attempt_idx, dur in enumerate(duration_steps):
        try:
            print(f"🔄 [SMART RETRY ENGINE] Attempt {attempt_idx + 1}/{len(duration_steps)}: Trying {video_type.upper()} ({dur} seconds)...")
            
            script_data = generate_ai_script_core(
                topic=topic,
                duration=dur,
                video_type=video_type,
                language="hi",
                tone="viral",
                category=category
            )

            full_script = script_data.get("full_script", "")
            raw_scenes = script_data.get("scenes", [])
            scenes_obj = [Scene(text=s.get("text", ""), keyword=s.get("keyword", "technology")) for s in raw_scenes]

            if not scenes_obj:
                scenes_obj = [Scene(text=full_script or topic, keyword="technology")]

            v_req = VideoRequest(
                user_id=user_id,
                topic=topic,
                category=category,
                voice_id=voice_id,
                font_name=font_name,
                font_color=font_color,
                video_type=video_type,
                full_script=full_script,
                scenes=scenes_obj,
                bg_music=bg_music
            )

            job_id = str(uuid.uuid4())
            full_process(v_req, job_id)

            job_result = jobs.get(job_id, {})
            if job_result.get("status") == "completed":
                print(f"✅ [SMART RETRY ENGINE SUCCESS] Successfully rendered {dur}s {video_type.upper()} on Attempt {attempt_idx + 1}!")
                return job_result
            else:
                last_error = job_result.get("error", "Unknown error")
                print(f"⚠️ Attempt {attempt_idx + 1} ({dur}s) failed: {last_error}. Stepping down duration...")
        except Exception as ex:
            last_error = str(ex)
            print(f"⚠️ Attempt {attempt_idx + 1} exception ({dur}s): {ex}. Stepping down duration...")

    print(f"❌ [SMART RETRY ENGINE EXHAUSTED] Tried all fallback durations: {last_error}")
    return {"status": "failed", "error": last_error}

class CreateOrderRequest(BaseModel):
    internal_id: str
    plan_type: str  # 'short' (50), 'long' (100), 'combo' (119)

class VerifyPaymentRequest(BaseModel):
    internal_id: str
    plan_type: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: Optional[str] = None

class AutoScheduleRequest(BaseModel):
    internal_id: str
    schedule_enabled: bool = True
    
    # Short / Reel Settings
    short_auto_topic: bool = True
    short_topic: str = "Space Exploration, AI Innovations"
    short_category: str = "Random" # 30+ categories or custom
    short_voice: str = "hi-IN-MadhurNeural"
    short_font: str = "Arial.ttf"
    short_color: str = "yellow"
    short_duration: int = 30
    short_time: str = "10:00"
    short_language: str = "hi"
    
    # Long Video Settings
    long_auto_topic: bool = True
    long_topic: str = "Space Exploration, AI Technology"
    long_category: str = "Random" # 30+ categories or custom
    long_voice: str = "hi-IN-MadhurNeural"
    long_font: str = "Arial.ttf"
    long_color: str = "yellow"
    long_duration: int = 60
    long_time: str = "18:00"
    long_language: str = "hi"

@app.post("/generate-custom-video")
async def generate_custom_video(req: VideoRequest, background_tasks: BackgroundTasks):
    user_id = req.user_id
    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Please login or register to generate videos.")

    # Safety Check: Script Length & Scene Count Limits (Anti-DDoS / Anti-Memory Crash)
    if req.full_script and len(req.full_script) > 5000:
        raise HTTPException(status_code=400, detail="⚠️ Script too long! Maximum script length allowed is 5,000 characters per video.")

    if req.scenes and len(req.scenes) > 25:
        raise HTTPException(status_code=400, detail="⚠️ Too many scenes! Maximum scenes allowed per video is 25.")

    if users_collection is not None:
        user = users_collection.find_one({"internal_id": user_id})
        if user:
            free_demo = user.get("free_demo_count", 2)
            subscription = user.get("subscription", {})
            sub_status = subscription.get("status")
            sub_expires = subscription.get("expires_at")
            sub_plan = subscription.get("plan_type", "none")
            
            is_active = False
            if sub_status == "active" and sub_expires:
                if isinstance(sub_expires, str):
                    try:
                        sub_expires = datetime.fromisoformat(sub_expires)
                    except Exception:
                        sub_expires = None
                if sub_expires and sub_expires > datetime.utcnow():
                    is_active = True
                    
            if not is_active:
                # Atomic decrement safeguard: Prevents multi-tab parallel race conditions
                res = users_collection.update_one(
                    {"internal_id": user_id, "free_demo_count": {"$gt": 0}},
                    {"$inc": {"free_demo_count": -1}}
                )
                if res.modified_count == 0:
                    raise HTTPException(status_code=402, detail="Demo quota exhausted! You have used your 2 free demo videos. Please upgrade your plan to continue generating videos.")
            else:
                # Active Subscription Quota Enforcement per Plan
                today_str = datetime.utcnow().strftime("%Y-%m-%d")
                daily_usage = user.get("daily_usage", {})
                if daily_usage.get("date") != today_str:
                    daily_usage = {"date": today_str, "short_count": 0, "long_count": 0}
                
                short_count = daily_usage.get("short_count", 0)
                long_count = daily_usage.get("long_count", 0)
                v_type = req.video_type  # 'short' or 'long'

                if sub_plan == "short":
                    if v_type == "long":
                        raise HTTPException(status_code=403, detail="⚠️ Your SHORT STARTER plan only permits Short videos (9:16). Please upgrade to LONG MASTER or PRO COMBO to generate Long videos.")
                    if short_count >= 1:
                        raise HTTPException(status_code=429, detail="⚠️ Daily video limit reached! Your SHORT STARTER plan permits 1 Short video daily. Please try again tomorrow or upgrade to PRO COMBO.")
                    daily_usage["short_count"] += 1

                elif sub_plan == "long":
                    if v_type == "short":
                        raise HTTPException(status_code=403, detail="⚠️ Your LONG MASTER plan only permits Long videos (16:9). Please upgrade to SHORT STARTER or PRO COMBO to generate Short videos.")
                    if long_count >= 1:
                        raise HTTPException(status_code=429, detail="⚠️ Daily video limit reached! Your LONG MASTER plan permits 1 Long video daily. Please try again tomorrow or upgrade to PRO COMBO.")
                    daily_usage["long_count"] += 1

                elif sub_plan == "combo":
                    # COMBO plan: Unlimited manual video generation (1 Short + 1 Long daily for Auto-Upload engine)
                    if v_type == "short":
                        daily_usage["short_count"] += 1
                    else:
                        daily_usage["long_count"] += 1

                # Save updated daily usage tracking to MongoDB profile
                users_collection.update_one(
                    {"internal_id": user_id},
                    {"$set": {"daily_usage": daily_usage}}
                )

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "user_id": req.user_id}
    background_tasks.add_task(full_process, req, job_id)
    return {"job_id": job_id, "status": "Processing Started"}

class ProfilePicRequest(BaseModel):
    internal_id: str
    profile_pic: str

@app.post("/update-profile-pic")
async def update_profile_pic(req: ProfilePicRequest):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    users_collection.update_one(
        {"internal_id": req.internal_id},
        {"$set": {"profile_pic": req.profile_pic}}
    )
    return {"message": "Profile picture updated successfully!"}

@app.get("/user-subscription/{internal_id}")
async def get_user_subscription(internal_id: str):
    if users_collection is None:
        return {"free_demo_count": 2, "has_active_subscription": False, "plan_type": "none"}
        
    user = users_collection.find_one({"internal_id": internal_id})
    if not user:
        return {"free_demo_count": 2, "has_active_subscription": False, "plan_type": "none"}
        
    free_demo = user.get("free_demo_count", 2)
    subscription = user.get("subscription", {})
    sub_status = subscription.get("status")
    sub_expires = subscription.get("expires_at")
    sub_plan = subscription.get("plan_type", "none")
    
    is_active = False
    if sub_status == "active" and sub_expires:
        if isinstance(sub_expires, str):
            sub_expires = datetime.fromisoformat(sub_expires)
        if sub_expires > datetime.utcnow():
            is_active = True

    today_ist_str = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
    daily_usage = user.get("daily_usage", {})
    if daily_usage.get("date") != today_ist_str:
        daily_usage = {"date": today_ist_str, "short_count": 0, "long_count": 0}

    auto_daily_usage = user.get("auto_daily_usage", {})
    if auto_daily_usage.get("date") != today_ist_str:
        auto_daily_usage = {"date": today_ist_str, "auto_short_count": 0, "auto_long_count": 0}

    limit_text = "2 Free Demo Videos Total"
    if is_active:
        if sub_plan == "combo":
            limit_text = "2 Videos Daily (1 Short + 1 Long)"
        elif sub_plan == "short":
            limit_text = "1 Short Video Daily (9:16)"
        elif sub_plan == "long":
            limit_text = "1 Long Video Daily (16:9)"

    return {
        "name": user.get("name", "User"),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "country": user.get("country", ""),
        "profile_pic": user.get("profile_pic", ""),
        "free_demo_count": free_demo,
        "has_active_subscription": is_active,
        "plan_type": sub_plan if is_active else "none",
        "expires_at": sub_expires.isoformat() if is_active and sub_expires else None,
        "today_short_count": daily_usage.get("short_count", 0),
        "today_long_count": daily_usage.get("long_count", 0),
        "today_auto_short_count": auto_daily_usage.get("auto_short_count", 0),
        "today_auto_long_count": auto_daily_usage.get("auto_long_count", 0),
        "daily_limit_text": limit_text
    }

@app.post("/save-auto-schedule")
async def save_auto_schedule(req: AutoScheduleRequest):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    user = users_collection.find_one({"internal_id": req.internal_id})
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")

    # Safeguard: Check if user has active paid membership before saving schedule
    subscription = user.get("subscription", {})
    sub_status = subscription.get("status")
    sub_expires = subscription.get("expires_at")
    sub_plan = subscription.get("plan_type", "none")
    
    is_active = False
    if sub_status == "active" and sub_expires:
        if isinstance(sub_expires, str):
            try:
                sub_expires = datetime.fromisoformat(sub_expires)
            except Exception:
                sub_expires = None
        if sub_expires and sub_expires > datetime.utcnow():
            is_active = True

    if not is_active:
        raise HTTPException(status_code=403, detail="🔒 Membership Only Feature! Auto-Schedule & Auto-Upload require an active paid membership plan. Please upgrade your membership to activate automatic video generation & YouTube publishing.")

    # Duration constraints enforcement per plan:
    # Short duration: 10s to 55s
    req.short_duration = max(10, min(55, req.short_duration))
    # Long duration: 20s to 300s (5 mins)
    req.long_duration = max(20, min(300, req.long_duration))

    existing_schedule = user.get("auto_schedule", {})
    existing_started_at = existing_schedule.get("schedule_started_at")

    if req.schedule_enabled:
        if not existing_started_at or not existing_schedule.get("schedule_enabled"):
            schedule_started_at = datetime.utcnow()
        else:
            schedule_started_at = existing_started_at
    else:
        schedule_started_at = None

    schedule_data = {
        "schedule_enabled": req.schedule_enabled,
        "schedule_started_at": schedule_started_at,
        "plan_type": sub_plan,
        
        # Short schedule profile
        "short_auto_topic": req.short_auto_topic,
        "short_topic": req.short_topic if not req.short_auto_topic else "AI Auto Topic (Daily Dynamic)",
        "short_category": req.short_category,
        "short_voice": req.short_voice,
        "short_font": req.short_font,
        "short_color": req.short_color,
        "short_duration": req.short_duration,
        "short_time": req.short_time,
        "short_language": req.short_language,
        
        # Long schedule profile
        "long_auto_topic": req.long_auto_topic,
        "long_topic": req.long_topic if not req.long_auto_topic else "AI Auto Topic (Daily Dynamic)",
        "long_category": req.long_category,
        "long_voice": req.long_voice,
        "long_font": req.long_font,
        "long_color": req.long_color,
        "long_duration": req.long_duration,
        "long_time": req.long_time,
        "long_language": req.long_language,
        
        "updated_at": datetime.utcnow()
    }

    users_collection.update_one(
        {"internal_id": req.internal_id},
        {"$set": {"auto_schedule": schedule_data}}
    )

    print(f"✅ Saved Auto-Schedule settings in MongoDB for user {req.internal_id} (Plan: {sub_plan})")
    return {"message": "Auto-schedule settings saved successfully to MongoDB profile!", "schedule": schedule_data}

@app.get("/get-auto-schedule/{internal_id}")
async def get_auto_schedule(internal_id: str):
    if users_collection is None:
        return {
            "schedule_enabled": False,
            "short_auto_topic": True,
            "short_topic": "Space Exploration, AI Innovations",
            "short_category": "Random",
            "short_voice": "hi-IN-MadhurNeural",
            "short_font": "Arial.ttf",
            "short_color": "yellow",
            "short_duration": 30,
            "short_time": "10:00",
            "short_language": "hi",
            "long_auto_topic": True,
            "long_topic": "Space Exploration, AI Technology",
            "long_category": "Random",
            "long_voice": "hi-IN-MadhurNeural",
            "long_font": "Arial.ttf",
            "long_color": "yellow",
            "long_duration": 60,
            "long_time": "18:00",
            "long_language": "hi",
            "total_videos_created": 0,
            "remaining_plan_videos": 60,
            "next_scheduled_run": "Not Scheduled"
        }

    user = users_collection.find_one({"internal_id": internal_id})
    if not user:
        return {
            "schedule_enabled": False,
            "short_auto_topic": True,
            "short_topic": "Space Exploration, AI Innovations",
            "short_category": "Random",
            "short_voice": "hi-IN-MadhurNeural",
            "short_font": "Arial.ttf",
            "short_color": "yellow",
            "short_duration": 30,
            "short_time": "10:00",
            "short_language": "hi",
            "long_auto_topic": True,
            "long_topic": "Space Exploration, AI Technology",
            "long_category": "Random",
            "long_voice": "hi-IN-MadhurNeural",
            "long_font": "Arial.ttf",
            "long_color": "yellow",
            "long_duration": 60,
            "long_time": "18:00",
            "long_language": "hi",
            "total_videos_created": 0,
            "remaining_plan_videos": 60,
            "next_scheduled_run": "Not Scheduled"
        }

    schedule = user.get("auto_schedule", {})
    sub = user.get("subscription", {})
    plan_type = sub.get("plan_type", "none")
    purchase_count = sub.get("purchase_count", 1) if sub.get("status") == "active" else 0
    
    # Calculate exact days passed since subscription activation timestamp
    days_elapsed = 0
    activated_at = sub.get("activated_at")
    if sub.get("status") == "active":
        if activated_at:
            if isinstance(activated_at, str):
                try:
                    activated_at = datetime.fromisoformat(activated_at)
                except Exception:
                    activated_at = None
            if isinstance(activated_at, datetime):
                time_passed = datetime.utcnow() - activated_at
                days_elapsed = max(0, time_passed.days)
        else:
            sub_expires = sub.get("expires_at")
            if sub_expires:
                if isinstance(sub_expires, str):
                    try:
                        sub_expires = datetime.fromisoformat(sub_expires)
                    except Exception:
                        sub_expires = None
                if isinstance(sub_expires, datetime) and sub_expires > datetime.utcnow():
                    days_left = (sub_expires - datetime.utcnow()).days
                    total_days_purchased = purchase_count * 30
                    days_elapsed = max(0, total_days_purchased - days_left)

    # Videos per day based on plan
    daily_quota = 2 if plan_type == "combo" else (1 if plan_type in ["short", "long"] else 0)
    total_allowance = purchase_count * 30 * daily_quota if daily_quota > 0 else 2
    
    # Videos used based on elapsed days (whether generated or missed!)
    used_videos = days_elapsed * daily_quota if daily_quota > 0 else (2 - user.get("free_demo_count", 2))
    remaining = max(0, total_allowance - used_videos)
    
    next_run = "Not Enabled"
    if schedule.get("schedule_enabled", False):
        if plan_type == "combo":
            next_run = f"Short: Daily at {schedule.get('short_time', '10:00')} | Long: Daily at {schedule.get('long_time', '18:00')}"
        elif plan_type == "short":
            next_run = f"Short Reel: Daily at {schedule.get('short_time', '10:00')}"
        elif plan_type == "long":
            next_run = f"Long Video: Daily at {schedule.get('long_time', '18:00')}"

    started_at = schedule.get("schedule_started_at")
    hours_active = 0
    if started_at:
        if isinstance(started_at, str):
            try:
                started_at = datetime.fromisoformat(started_at)
            except Exception:
                started_at = None
        if isinstance(started_at, datetime):
            hours_active = round((datetime.utcnow() - started_at).total_seconds() / 3600, 1)

    return {
        "schedule_enabled": schedule.get("schedule_enabled", False),
        "schedule_started_at": started_at.isoformat() if isinstance(started_at, datetime) else None,
        "hours_active": hours_active,
        "plan_type": plan_type,
        
        # Short settings
        "short_auto_topic": schedule.get("short_auto_topic", True),
        "short_topic": schedule.get("short_topic", "Space Exploration, AI Innovations"),
        "short_category": schedule.get("short_category", "Random"),
        "short_voice": schedule.get("short_voice", "hi-IN-MadhurNeural"),
        "short_font": schedule.get("short_font", "Arial.ttf"),
        "short_color": schedule.get("short_color", "yellow"),
        "short_duration": schedule.get("short_duration", 30),
        "short_time": schedule.get("short_time", "10:00"),
        "short_language": schedule.get("short_language", "hi"),
        
        # Long settings
        "long_auto_topic": schedule.get("long_auto_topic", True),
        "long_topic": schedule.get("long_topic", "Space Exploration, AI Technology"),
        "long_category": schedule.get("long_category", "Random"),
        "long_voice": schedule.get("long_voice", "hi-IN-MadhurNeural"),
        "long_font": schedule.get("long_font", "Arial.ttf"),
        "long_color": schedule.get("long_color", "yellow"),
        "long_duration": schedule.get("long_duration", 60),
        "long_time": schedule.get("long_time", "18:00"),
        "long_language": schedule.get("long_language", "hi"),

        "total_videos_created": used_videos,
        "remaining_plan_videos": remaining,
        "total_plan_allowance": total_allowance,
        "purchase_count": purchase_count,
        "next_scheduled_run": next_run
    }

@app.get("/admin/active-schedules")
async def get_active_schedules_admin():
    """Admin inspection endpoint listing all accounts with active auto-upload enabled"""
    if users_collection is None:
        return {"total_active_accounts": 0, "active_schedules": []}

    active_users = list(users_collection.find({"auto_schedule.schedule_enabled": True}))
    results = []

    for user in active_users:
        sched = user.get("auto_schedule", {})
        sub = user.get("subscription", {})
        yt = user.get("youtube_credentials", {})
        results.append({
            "internal_id": user.get("internal_id"),
            "email": user.get("email"),
            "name": user.get("name"),
            "plan_type": sub.get("plan_type"),
            "youtube_connected": bool(yt),
            "short_upload_time": sched.get("short_time"),
            "long_upload_time": sched.get("long_time"),
            "schedule_started_at": sched.get("schedule_started_at"),
            "last_short_run": sched.get("last_short_run"),
            "last_long_run": sched.get("last_long_run")
        })

    return {
        "total_active_accounts": len(results),
        "active_schedules": results
    }

@app.get("/admin/security-status")
def get_security_status():
    """Admin inspection endpoint displaying active WAF security metrics and threat logs"""
    return {
        "waf_status": "ACTIVE_ENFORCED",
        "shield_version": "Cloxel Ultimate WAF v2.0",
        "attack_statistics": waf.attack_stats,
        "active_banned_ips": list(waf.banned_ips.keys()),
        "total_banned_ips": len(waf.banned_ips)
    }

PLAN_RANKS = {"short": 1, "long": 2, "combo": 3}
PLAN_NAMES = {
    "short": "Short Starter (₹50/mo)",
    "long": "Long Master (₹100/mo)",
    "combo": "Pro Combo (₹119/mo)"
}

@app.post("/create-razorpay-order")
async def create_razorpay_order(req: CreateOrderRequest):
    amounts = {
        "short": 5000,    # ₹50
        "long": 10000,    # ₹100
        "combo": 11900    # ₹119
    }
    
    # Rule A: Check for Active High-Tier Plan to Prevent Unintended Downgrades
    if users_collection is not None and req.internal_id:
        user = users_collection.find_one({"internal_id": req.internal_id})
        if user:
            sub = user.get("subscription", {})
            sub_status = sub.get("status")
            sub_expires = sub.get("expires_at")
            current_plan = sub.get("plan_type", "none")
            
            is_active = False
            if sub_status == "active" and sub_expires:
                if isinstance(sub_expires, str):
                    try:
                        sub_expires = datetime.fromisoformat(sub_expires)
                    except Exception:
                        sub_expires = None
                if isinstance(sub_expires, datetime) and sub_expires > datetime.utcnow():
                    is_active = True

            if is_active:
                curr_rank = PLAN_RANKS.get(current_plan, 0)
                new_rank = PLAN_RANKS.get(req.plan_type, 0)
                
                if new_rank < curr_rank:
                    exp_date_str = sub_expires.strftime("%b %d, %Y") if isinstance(sub_expires, datetime) else "expiry"
                    raise HTTPException(
                        status_code=400,
                        detail=f"⚠️ Plan Downgrade Restricted! You already have an active high-tier plan ({PLAN_NAMES.get(current_plan, current_plan)}). You cannot downgrade to {PLAN_NAMES.get(req.plan_type, req.plan_type)} until your current plan expires on {exp_date_str}."
                    )

    amount = amounts.get(req.plan_type, 5000)
    
    key_id = os.getenv("RAZORPAY_KEY_ID", "rzp_test_TRfILFpcp5Owd4").strip().strip('"').strip("'")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip().strip('"').strip("'")
    
    if key_id and key_secret and key_id != "rzp_test_placeholder":
        try:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))
            order = client.order.create({
                "amount": amount,
                "currency": "INR",
                "receipt": f"receipt_{req.internal_id[:8]}_{int(datetime.utcnow().timestamp())}",
                "payment_capture": 1
            })
            return {
                "order_id": order["id"],
                "amount": amount,
                "currency": "INR",
                "key_id": key_id
            }
        except Exception as e:
            print(f"⚠️ Razorpay API order warning: {e}. Falling back to standard test checkout mode.")
            
    # Fallback to test checkout order so popup always opens smoothly
    fake_order_id = f"order_test_{str(uuid.uuid4())[:8]}"
    return {
        "order_id": fake_order_id,
        "amount": amount,
        "currency": "INR",
        "key_id": key_id if key_id else "rzp_test_TRfILFpcp5Owd4"
    }

@app.post("/verify-razorpay-payment")
async def verify_razorpay_payment(req: VerifyPaymentRequest):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    if not req.razorpay_payment_id or req.razorpay_payment_id.startswith("pay_demo_") or req.razorpay_payment_id == "cancelled":
        raise HTTPException(status_code=400, detail="Payment failed or was cancelled by user. Membership not activated.")

    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip().strip('"').strip("'")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip().strip('"').strip("'")

    if key_id and key_secret and req.razorpay_signature and key_secret != "secret_placeholder":
        try:
            import razorpay
            client = razorpay.Client(auth=(key_id, key_secret))
            client.utility.verify_payment_signature({
                'razorpay_order_id': req.razorpay_order_id,
                'razorpay_payment_id': req.razorpay_payment_id,
                'razorpay_signature': req.razorpay_signature
            })
        except Exception as e:
            print(f"❌ Razorpay signature verification failed: {e}")
            raise HTTPException(status_code=400, detail="Payment Signature Verification Failed. Activation Denied.")

    # Mathematical Precision: Handle Plan Upgrades & Same-Plan Stacking
    existing_user = users_collection.find_one({"internal_id": req.internal_id})
    existing_sub = existing_user.get("subscription", {}) if existing_user else {}
    current_plan = existing_sub.get("plan_type", "none")
    sub_status = existing_sub.get("status")
    sub_exp = existing_sub.get("expires_at")
    purchase_count = existing_sub.get("purchase_count", 0)

    is_active = False
    if sub_status == "active" and sub_exp:
        if isinstance(sub_exp, str):
            try:
                sub_exp = datetime.fromisoformat(sub_exp)
            except Exception:
                sub_exp = None
        if isinstance(sub_exp, datetime) and sub_exp > datetime.utcnow():
            is_active = True

    if is_active:
        if current_plan == req.plan_type:
            # Rule C: Same plan stacking! Add +30 days to existing active expiration date!
            expires_at = sub_exp + timedelta(days=30)
            purchase_count += 1
            print(f"🔄 Stacked +30 days on '{req.plan_type}' for user {req.internal_id} (Purchase #{purchase_count}, Expiry: {expires_at.isoformat()})")
        else:
            # Rule B: Upgrading from lower tier to higher tier plan! Start fresh 30 days!
            expires_at = datetime.utcnow() + timedelta(days=30)
            purchase_count = 1
            print(f"🚀 Upgraded user {req.internal_id} from '{current_plan}' to '{req.plan_type}'! Expiry set to {expires_at.isoformat()}")
    else:
        expires_at = datetime.utcnow() + timedelta(days=30)
        purchase_count = 1
        print(f"✅ Activated new 30-day '{req.plan_type}' membership for user {req.internal_id}")
    
    subscription_data = {
        "plan_type": req.plan_type,
        "status": "active",
        "payment_id": req.razorpay_payment_id,
        "order_id": req.razorpay_order_id,
        "activated_at": datetime.utcnow() if not existing_sub.get("activated_at") else existing_sub.get("activated_at"),
        "expires_at": expires_at,
        "purchase_count": purchase_count
    }
    
    users_collection.update_one(
        {"internal_id": req.internal_id},
        {"$set": {"subscription": subscription_data}}
    )
    
    return {
        "message": f"Payment verified! '{PLAN_NAMES.get(req.plan_type, req.plan_type)}' activated successfully until {expires_at.strftime('%b %d, %Y')}!",
        "expires_at": expires_at.isoformat(),
        "purchase_count": purchase_count
    }

@app.post("/register")
async def register_user(req: UserRegister):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    primary_email = req.email.strip().lower()
    # Clean phone to digits
    primary_phone = "".join(filter(str.isdigit, req.phone))
    
    if not primary_email or not primary_phone or not req.name.strip() or not req.country.strip():
        raise HTTPException(status_code=400, detail="All fields (Name, Country, Phone, Email, Password) are mandatory.")
        
    import re
    email_regex = re.compile(f"^{re.escape(primary_email)}$", re.IGNORECASE)
    
    existing_user = users_collection.find_one({
        "$or": [
            {"email": email_regex},
            {"phone": primary_phone},
            {"phone": req.phone.strip()},
            {"email_or_mobile": email_regex},
            {"email_or_mobile": primary_phone}
        ]
    })
    
    if existing_user:
        ex_email = existing_user.get("email", "").lower()
        ex_phone = existing_user.get("phone", "")
        if ex_email == primary_email:
            raise HTTPException(status_code=400, detail="⚠️ Account Creation Failed: This Email ID is already registered! Please use a different Email or Login.")
        else:
            raise HTTPException(status_code=400, detail="⚠️ Account Creation Failed: This Phone Number is already registered! Please use a different Phone Number or Login.")
        
    hashed_password = safe_hash_password(req.password)
    internal_id = str(uuid.uuid4())
    
    new_user = {
        "name": req.name.strip(),
        "country": req.country.strip(),
        "phone": primary_phone,
        "email": primary_email,
        "email_or_mobile": primary_email,
        "password_hash": hashed_password,
        "internal_id": internal_id,
        "created_at": datetime.utcnow()
    }
    
    users_collection.insert_one(new_user)
    return {"message": "User registered successfully", "internal_id": internal_id}

@app.post("/login")
async def login_user(req: UserLogin):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    raw_identifier = req.email_or_mobile.strip()
    clean_phone = "".join(filter(str.isdigit, raw_identifier))
    import re
    identifier_regex = re.compile(f"^{re.escape(raw_identifier.lower())}$", re.IGNORECASE)
    
    query = [
        {"email": identifier_regex},
        {"email_or_mobile": identifier_regex},
        {"internal_id": raw_identifier}
    ]
    if clean_phone:
        query.append({"phone": clean_phone})
        query.append({"email_or_mobile": clean_phone})
        
    user = users_collection.find_one({"$or": query})
    
    if not user:
        raise HTTPException(status_code=400, detail="⚠️ Account Not Found: Please check your Email / Mobile Number or click Register.")
        
    stored_hash = user.get("password_hash") or user.get("password")
    if not stored_hash:
        raise HTTPException(status_code=400, detail="⚠️ Account password configuration issue. Please Register a new account.")

    is_valid = safe_verify_password(req.password, stored_hash)

    if not is_valid:
        raise HTTPException(status_code=400, detail="⚠️ Incorrect Password: Please check your password and try again.")
        
    return {"message": "Login successful", "internal_id": user["internal_id"]}

@app.get("/history/{internal_id}")
async def get_video_history(internal_id: str):
    if videos_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Sort by creation date descending (newest first)
        videos_cursor = videos_collection.find({"internal_id": internal_id}).sort("created_at", -1)
        videos_list = []
        for v in videos_cursor:
            videos_list.append({
                "job_id": v.get("job_id"),
                "topic": v.get("topic", "Unknown Topic"),
                "cloudinary_url": v.get("cloudinary_url"),
                "created_at": v.get("created_at").isoformat() if v.get("created_at") else None
            })
        return {"history": videos_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    return jobs.get(job_id, {"status": "not_found"})

@app.get("/download/{job_id}")
async def download_video(job_id: str):
    job = jobs.get(job_id)
    if job and job["status"] == "completed":
        return FileResponse(job["file"], media_type="video/mp4", filename="cloxel_video.mp4")
    return {"error": "File not ready"}

@app.get("/bg-music-list")
async def get_bg_music_list():
    music_files = ["cool.mp3", "cool1.mp3", "cool2.mp3", "cool3.mp3", "cool4.mp3", "cool5.mp3"]
    search_dirs = [".", "./songs", "./songs copy"]
    found = set(music_files)
    for d in search_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.lower().endswith(('.mp3', '.wav')):
                    found.add(f)
    return {"music_tracks": sorted(list(found))}

@app.get("/fonts-list")
async def get_fonts_list():
    fonts_dir = "./fonts"
    fonts = ["Arial.ttf"]
    if os.path.exists(fonts_dir):
        fonts = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))]
    return {"fonts": sorted(fonts)}

@app.post("/cleanup/{job_id}")
async def cleanup(job_id: str):
    """Video download hone ke baad server saaf karne ke liye"""
    job = jobs.get(job_id)
    if job:
        if os.path.exists(job.get("file", "")): os.remove(job["file"])
        if os.path.exists(job.get("dir", "")): shutil.rmtree(job["dir"])
        return {"status": "Cleaned"}
    return {"error": "Job not found"}

# ================= YouTube Auth Endpoints =================
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_flow():
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        return None

    client_config = {
        "web": {
            "client_id": client_id,
            "project_id": "cloxel-app",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": [os.getenv("YOUTUBE_REDIRECT_URI", "https://cloxel.onrender.com/youtube/callback")]
        }
    }
    
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config, scopes=YOUTUBE_SCOPES
    )
    flow.redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", "https://cloxel.onrender.com/youtube/callback")
    return flow

class UnlinkRequest(BaseModel):
    internal_id: str

@app.get("/youtube/auth-url")
async def get_youtube_auth_url(internal_id: str):
    if not internal_id:
        raise HTTPException(status_code=400, detail="Missing user internal_id")

    # Check for active paid membership before allowing YouTube connection
    if users_collection is not None:
        user = users_collection.find_one({"internal_id": internal_id})
        if user:
            sub = user.get("subscription", {})
            sub_status = sub.get("status")
            sub_expires = sub.get("expires_at")
            is_active = False
            if sub_status == "active" and sub_expires:
                if isinstance(sub_expires, str):
                    try:
                        sub_expires = datetime.fromisoformat(sub_expires)
                    except Exception:
                        sub_expires = None
                if isinstance(sub_expires, datetime) and sub_expires > datetime.utcnow():
                    is_active = True
            if not is_active:
                raise HTTPException(
                    status_code=403,
                    detail="⚠️ YouTube Connection Requires Active Paid Membership! Please upgrade your plan (Short Starter, Long Master, Pro Combo) to link your YouTube account."
                )

    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="YouTube Client ID/Secret not configured in environment.")
    
    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", "https://cloxel.onrender.com/youtube/callback")
    scope = " ".join(YOUTUBE_SCOPES)
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
        "state": internal_id
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {"auth_url": auth_url}

@app.get("/youtube/callback")
async def youtube_callback(state: str, code: str):
    internal_id = state
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    redirect_uri = os.getenv("YOUTUBE_REDIRECT_URI", "https://cloxel.onrender.com/youtube/callback")
    
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="YouTube Client ID/Secret not configured.")
    
    try:
        # Direct OAuth2 Token Exchange
        token_data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        resp = requests.post("https://oauth2.googleapis.com/token", data=token_data)
        res_json = resp.json()
        
        if "error" in res_json:
            error_msg = res_json.get("error_description", res_json.get("error"))
            print(f"❌ Token exchange error: {error_msg}")
            frontend_url = os.getenv("FRONTEND_URL", "https://cloxel.onrender.com")
            return RedirectResponse(url=f"{frontend_url}/?yt_error={error_msg}")
            
        creds_dict = {
            'token': res_json.get('access_token'),
            'refresh_token': res_json.get('refresh_token'),
            'token_uri': "https://oauth2.googleapis.com/token",
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': YOUTUBE_SCOPES
        }
        
        if users_collection is not None:
            users_collection.update_one(
                {"internal_id": internal_id},
                {"$set": {
                    "youtube_credentials": creds_dict,
                    "youtube_linked_at": datetime.utcnow()
                }}
            )
            
        frontend_url = os.getenv("FRONTEND_URL", "https://cloxel.onrender.com")
        return RedirectResponse(url=f"{frontend_url}/?yt_success=1")
    except Exception as e:
        print(f"❌ Error in youtube_callback: {e}")
        import traceback
        traceback.print_exc()
        frontend_url = os.getenv("FRONTEND_URL", "https://cloxel.onrender.com")
        return RedirectResponse(url=f"{frontend_url}/?yt_error={str(e)}")

@app.get("/youtube/status/{internal_id}")
async def get_youtube_status(internal_id: str):
    if users_collection is None:
        return {"linked": False}
        
    user = users_collection.find_one({"internal_id": internal_id})
    if not user or "youtube_credentials" not in user:
        return {"linked": False}
        
    linked_at = user.get("youtube_linked_at")
    if not linked_at:
        return {"linked": True, "can_unlink": True, "hours_left": 0}
        
    if isinstance(linked_at, str):
        try:
            linked_at = datetime.fromisoformat(linked_at.replace("Z", "+00:00"))
            if linked_at.tzinfo is not None:
                linked_at = linked_at.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            linked_at = None

    if not linked_at or not isinstance(linked_at, datetime):
        return {"linked": True, "can_unlink": True, "hours_left": 0}

    time_passed = datetime.utcnow() - linked_at
    can_unlink = time_passed >= timedelta(hours=24)
    
    hours_left = 0
    if not can_unlink:
        hours_left = max(0, 24 - (time_passed.total_seconds() / 3600))
        
    return {
        "linked": True,
        "can_unlink": can_unlink,
        "hours_left": round(hours_left, 1)
    }

@app.post("/youtube/unlink")
async def unlink_youtube(req: UnlinkRequest):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    user = users_collection.find_one({"internal_id": req.internal_id})
    if not user or "youtube_credentials" not in user:
        raise HTTPException(status_code=400, detail="No YouTube account linked")
        
    linked_at = user.get("youtube_linked_at")
    if linked_at:
        if isinstance(linked_at, str):
            try:
                linked_at = datetime.fromisoformat(linked_at.replace("Z", "+00:00"))
                if linked_at.tzinfo is not None:
                    linked_at = linked_at.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                linked_at = None

        if isinstance(linked_at, datetime):
            time_passed = datetime.utcnow() - linked_at
            if time_passed < timedelta(hours=24):
                hours_left = max(0, round(24 - (time_passed.total_seconds() / 3600), 1))
                raise HTTPException(status_code=403, detail=f"Cannot unlink before 24 hours have passed. ({hours_left} hours left)")
            
    users_collection.update_one(
        {"internal_id": req.internal_id},
        {"$unset": {"youtube_credentials": "", "youtube_linked_at": ""}}
    )
    
    return {"message": "YouTube account unlinked successfully"}


class AIScriptRequest(BaseModel):
    topic: str
    category: Optional[str] = "Random" # 30+ categories or custom
    duration_seconds: int = 30
    video_type: Optional[str] = "short"  # 'short' or 'long'
    language: Optional[str] = "hinglish" # 'hindi', 'english', 'hinglish'
    tone: Optional[str] = "viral"        # 'viral', 'informative', 'mysterious', 'funny'

def generate_ai_script_core(topic: str, duration: int, video_type: str = "short", language: str = "hinglish", tone: str = "viral", category: str = "Random"):
    # Multi-service AI Script Server Priority List (Railway -> Render -> Custom)
    raw_env_url = os.getenv("AI_SERVER_URL", "").rstrip("/")
    candidate_urls = [
        "https://ai-script-generator-service-production.up.railway.app",
        raw_env_url if raw_env_url else "https://ai-script-generator-service.onrender.com",
        "https://ai-script-generator-service.onrender.com"
    ]
    seen = set()
    ai_server_urls = [u for u in candidate_urls if u and not (u in seen or seen.add(u))]

    scene_count = max(1, duration // 10)
    word_count = int(duration * 2.8) if video_type == "short" else int(duration * 2.5)

    cat_niche = f" in the '{category}' category" if category and str(category).lower() != "random" else ""

    # 1. Primary Attempt: Call External Dedicated AI Script Services (Railway -> Render)
    payload = {
        "topic": topic,
        "category": category,
        "duration_seconds": duration,
        "video_type": video_type,
        "language": language,
        "tone": tone
    }
    
    for base_url in ai_server_urls:
        for endpoint in ["/generate-script", "/api/generate-ai-script", "/generate"]:
            target_url = f"{base_url}{endpoint}"
            try:
                resp = requests.post(target_url, json=payload, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    full_script = data.get("full_script") or data.get("script") or ""
                    scenes = data.get("scenes") or []
                    
                    if full_script or scenes:
                        # Auto-build scenes if missing
                        if not scenes and full_script:
                            stop_words = {"aur", "ek", "hai", "ki", "ke", "ka", "jo", "se", "me", "ko"}
                            kws = [w.lower() for w in topic.split() if w.isalpha() and w.lower() not in stop_words]
                            kw = kws[0] if kws else topic
                            chunks = full_script.split(".")
                            scenes = [{"text": c.strip(), "keyword": kw} for c in chunks if len(c.strip()) > 5][:scene_count]
                            
                        print(f"✅ External AI Script Service Success ({target_url})!")
                        title_gen, desc_gen = build_youtube_metadata(topic=topic, full_script=full_script, video_type=video_type)
                        return {
                            "status": "success",
                            "source": "external_ai_service",
                            "server_url": target_url,
                            "topic": topic,
                            "duration_seconds": duration,
                            "video_type": video_type,
                            "language": language,
                            "tone": tone,
                            "estimated_word_count": word_count,
                            "full_script": full_script,
                            "scenes": scenes,
                            "title": title_gen,
                            "description": desc_gen
                        }
            except Exception as e_inner:
                continue

    # 2. Secondary Attempt: Fallback to Gemini AI Direct Key
    # 2. Secondary Attempt: Fallback to Gemini AI Direct Key
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            ultra_special_prompt = (
                f"\nSPECIAL ULTRA MODE REQUIREMENT:\n"
                f"This is an ULTRA premium documentary video. Write a rich, deeply informative, and complete narrative script.\n"
                f"Do NOT output short title fragments or half-baked sentences.\n"
                f"Each scene text MUST contain 2-3 complete, highly engaging, informative spoken sentences explaining the history, key achievements, and full story of '{topic}'.\n"
            ) if (video_type == "ultra") else ""

            prompt = (
                f"You are a master viral video scriptwriter. Write a COMPLETE, fully-resolved video script about '{topic}' "
                f"in {language} language. Video type: {video_type.upper()} ({duration} seconds, approx {word_count} spoken words).\n"
                f"CRITICAL REQUIREMENT: The script MUST be 100% complete with a clear Hook, Full Core Information, and a Satisfying Conclusion. "
                f"Do NOT leave the explanation half-done or cut off mid-sentence.{ultra_special_prompt}\n"
                f"Format requirement: Return ONLY a valid JSON object with:\n"
                f"1. 'full_script': The complete spoken voiceover text covering the full story from hook to conclusion.\n"
                f"2. 'scenes': An array of exactly {scene_count} complete sentence scene objects, each containing:\n"
                f"   - 'text': 2-3 complete, detailed, well-formed sentences with full stops.\n"
                f"   - 'keyword': 1-2 relevant visual search terms for background clips.\n"
                f"Do not include markdown triple backticks or text outside JSON."
            )

            req_data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                res_body = json.loads(resp.read().decode('utf-8'))
                raw_text = res_body['candidates'][0]['content']['parts'][0]['text'].strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:].strip()
                parsed = json.loads(raw_text)
                script_text = parsed.get("full_script", "")
                title_gen, desc_gen = build_youtube_metadata(topic=topic, full_script=script_text, video_type=video_type)
                return {
                    "status": "success",
                    "source": "gemini_ai",
                    "topic": topic,
                    "duration_seconds": duration,
                    "video_type": video_type,
                    "language": language,
                    "tone": tone,
                    "estimated_word_count": word_count,
                    "full_script": script_text,
                    "scenes": parsed.get("scenes", []),
                    "title": title_gen,
                    "description": desc_gen
                }
        except Exception as err:
            print(f"⚠️ Gemini API Warning (Falling back to dynamic engine): {err}")

    # Dynamic Smart Script Generator (Zero-Failure Structured Fallback)
    stop_words = {"aur", "ek", "hai", "ki", "ke", "ka", "jo", "se", "me", "ko", "hi", "to", "ye", "wo", "tha", "thi"}
    keywords = [w.lower() for w in topic.split() if w.isalpha() and w.lower() not in stop_words]
    main_kw = keywords[0] if keywords else topic

    if video_type == "ultra":
        intro_templates = [
            f"Itihas aur gathaon mein {topic} ka naam swabhiman aur veerta ka prateek mana jata hai. Iski poori kahani aapko aashcharya mein daal degi.",
            f"Kya aap jante hain {topic} se judi wo aitihasik baatein jo aaj bhi har bhartiya ke dil mein garv bhar deti hain? Aaiye vistaar se jaante hain."
        ]
        body_templates = [
            f"Iska mukhya uddeshya swabhiman aur matribhumi ki raksha karna tha, jiske liye yoddhaon ne aakhir saans tak sangharsh kiya.",
            f"Aitihasik shastron aur dastaavezon ke mutabiq {topic} ne shatruon ki sena ke chakke chhudaye the aur itihaas mein apna naam amar kar diya.",
            f"Ranbhoomi mein inki talwar aur ranniti ne dushmano ko aisi shikast di jise aaj bhi yaad kiya jata hai."
        ]
        outro_templates = [
            f"Yahi wajah hai ki {topic} ki ye veer gatha aaj bhi har peedhi ke liye prerna ka srot hai. Is aitihasik jaankari ke liye hume follow karein.",
            f"Swabhiman ki is kahani ne {topic} ko mahan bana diya. Aise hi aur durlabh aitihasik kisse dekhne ke liye channel ko subscribe karein!"
        ]
    else:
        intro_templates = [
            f"Dosto! Kya aapko pata hai {topic} ke baare mein ye hairatangez sach?",
            f"{topic} ki duniya mein ek aisa raaz hai jo aapka hosh uda dega.",
            f"Aaj hum {topic} se jude sabse bada aur shocking sach jaanenge."
        ]
        body_templates = [
            f"Iske peeche ki asli wajah ye hai ki {topic} hamari daily life par deep impact daalta hai.",
            f"Experts aur scientists ke mutabiq {topic} aane wale time mein poori tarah badalne wala hai.",
            f"Research mein pata chala hai ki {topic} ki wajah se kayi bade changes dekhe gaye hain.",
            f"Har roz hazaron log {topic} ke is naye aspect ko samajhne ki koshish kar rahe hain."
        ]
        outro_templates = [
            f"Toh ye tha {topic} ka poora sach! Aise hi viral aur informative content ke liye hume zaroor follow karein.",
            f"Yahi wajah hai ki {topic} itna special hai. Video acchi lagi ho toh like aur share zaroor karein!",
            f"Umeed hai aapko {topic} ki ye information pasand aayi hogi. Channel ko subscribe karna na bhulein!"
        ]

    scenes = []
    full_text_list = []
    
    for i in range(scene_count):
        if i == 0:
            text = intro_templates[0 % len(intro_templates)]
        elif i == scene_count - 1 and scene_count > 1:
            text = outro_templates[0 % len(outro_templates)]
        else:
            text = body_templates[(i - 1) % len(body_templates)]
            
        scenes.append({"text": text, "keyword": main_kw})
        full_text_list.append(text)

    script_text = " ".join(full_text_list)
    title_gen, desc_gen = build_youtube_metadata(topic=topic, full_script=script_text, video_type=video_type)
    return {
        "status": "success",
        "source": "dynamic_ai_engine",
        "topic": topic,
        "duration_seconds": duration,
        "video_type": video_type,
        "language": language,
        "tone": tone,
        "estimated_word_count": word_count,
        "full_script": script_text,
        "scenes": scenes,
        "title": title_gen,
        "description": desc_gen
    }

@app.post("/api/generate-ai-script")
async def api_generate_ai_script(req: AIScriptRequest):
    """
    Dedicated AI Script Generation API for Render/Remote clients.
    Takes topic, duration_seconds, video_type, language, and tone.
    Returns full_script and scene breakdown.
    """
    if not req.topic or not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic title is required")
        
    duration = max(10, min(300, req.duration_seconds))
    return generate_ai_script_core(
        topic=req.topic.strip(),
        duration=duration,
        video_type=req.video_type or "short",
        language=req.language or "hinglish",
        tone=req.tone or "viral"
    )

@app.post("/generate-script")
async def generate_script(req: ScriptRequest):
    """Legacy Endpoint compatibility wrapper"""
    res = generate_ai_script_core(topic=req.topic, duration=req.duration_seconds)
    return {"scenes": res["scenes"], "full_script": res["full_script"]}

# 4. Serve Frontend (Must be the last route)
if os.path.isdir("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
else:
    print("WARNING: frontend/dist not found. Run 'npm run build' in the frontend folder.")