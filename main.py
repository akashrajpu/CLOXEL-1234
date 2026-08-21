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
from fastapi import FastAPI, BackgroundTasks, HTTPException
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
scheduler.start()

# 3. Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# 1. CORS Setup - Iske bina frontend connect nahi hoga!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        
        # Scenes ki taiyari
        scenes_data = []
        if req.video_type == "long" and req.full_script:
            import re
            # Script ko full stop, comma, ya new lines se todna
            raw_chunks = re.split(r'[.|,:\n]', req.full_script)
            stop_words = {"aur", "ek", "hai", "ki", "ke", "ka", "jo", "se", "me", "ko", "hi", "to", "ye", "wo", "tha", "thi", "hain", "kya", "toh", "liye", "bhi", "yeh", "kuch", "hoti", "hain", "mil", "sakti"}
            
            for chunk in raw_chunks:
                chunk = chunk.strip()
                if len(chunk) < 5: continue
                
                # Basic Keyword Extraction: Pick the longest word that isn't a stop word
                words = [w.lower() for w in chunk.split() if w.isalpha() and w.lower() not in stop_words]
                keyword = "technology" # Fallback keyword
                if words:
                    words.sort(key=len, reverse=True)
                    keyword = words[0]
                    
                scenes_data.append({"text": chunk, "keyword": keyword})
                
            if not scenes_data:
                scenes_data = [{"text": req.full_script, "keyword": "technology"}]
        else:
            scenes_data = [{"text": s.text, "keyword": s.keyword} for s in req.scenes]
        
        taiyaar_scenes = []
        for i, sc in enumerate(scenes_data):
            a_path = os.path.join(job_dir, f"audio_{i}.mp3")
            v_path = os.path.join(job_dir, f"video_{i}.mp4")
            
            # Custom settings apply karna
            make_audio(sc["text"], a_path, req.voice_id)
            orientation = "landscape" if req.video_type == "long" else "portrait"
            v_paths = fetch_videos(sc["keyword"], v_path, orientation=orientation, category=req.category or "Random")
            
            if os.path.exists(a_path):
                if not v_paths:
                    # Internal fail-safe visual canvas fallback if no API key/media available
                    fallback_img_path = os.path.join(job_dir, f"fallback_canvas_{i}.jpg")
                    from PIL import Image
                    target_w, target_h = (1280, 720) if req.video_type == "long" else (720, 1280)
                    blank_img = Image.new('RGB', (target_w, target_h), color=(15, 10, 35))
                    blank_img.save(fallback_img_path)
                    v_paths = [fallback_img_path]

                taiyaar_scenes.append({
                    "audio": a_path, 
                    "video": v_paths, 
                    "text": sc["text"]
                })

        if taiyaar_scenes:
            output_file = f"output_{job_id}.mp4"
            # Editor ko user ki choice bhejna (font, color, bg_music)
            target_size = (1280, 720) if req.video_type == "long" else (720, 1280)
            adjusted_font_size = int(req.font_size * 0.7) if req.video_type == "long" else req.font_size
            merge_and_export(taiyaar_scenes, output_file, font_path=f"./fonts/{req.font_name}", color=req.font_color, font_size=adjusted_font_size, target_size=target_size, bg_music=req.bg_music) 
            
            # Upload to Cloudinary
            cloudinary_url = None
            try:
                upload_result = cloudinary.uploader.upload(output_file, resource_type="video")
                cloudinary_url = upload_result.get("secure_url")
            except Exception as e:
                print(f"Cloudinary upload failed: {e}")
                
            jobs[job_id] = {"status": "completed", "file": output_file, "dir": job_dir, "cloudinary_url": cloudinary_url}
            
            # Save to Video History in MongoDB
            if videos_collection is not None and req.user_id != "anonymous":
                try:
                    video_title = req.topic if req.topic else (req.full_script[:30] if req.full_script else (taiyaar_scenes[0]["text"][:30] if taiyaar_scenes else "Generated Video"))
                    videos_collection.insert_one({
                        "internal_id": req.user_id,
                        "job_id": job_id,
                        "topic": video_title,
                        "cloudinary_url": cloudinary_url,
                        "created_at": datetime.utcnow()
                    })
                    print(f"✅ Video history saved to MongoDB for user {req.user_id}: {video_title}")
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

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    daily_usage = user.get("daily_usage", {})
    if daily_usage.get("date") != today_str:
        daily_usage = {"date": today_str, "short_count": 0, "long_count": 0}

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

    schedule_data = {
        "schedule_enabled": req.schedule_enabled,
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

    return {
        "schedule_enabled": schedule.get("schedule_enabled", False),
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

@app.post("/create-razorpay-order")
async def create_razorpay_order(req: CreateOrderRequest):
    amounts = {
        "short": 5000,    # ₹50
        "long": 10000,    # ₹100
        "combo": 11900    # ₹119
    }
    
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

    # Check if user already has an active subscription to extend duration stack!
    existing_user = users_collection.find_one({"internal_id": req.internal_id})
    existing_sub = existing_user.get("subscription", {}) if existing_user else {}
    purchase_count = existing_sub.get("purchase_count", 0) + 1

    current_expires = None
    if existing_sub.get("status") == "active" and existing_sub.get("expires_at"):
        sub_exp = existing_sub.get("expires_at")
        if isinstance(sub_exp, str):
            try:
                sub_exp = datetime.fromisoformat(sub_exp)
            except Exception:
                sub_exp = None
        if sub_exp and sub_exp > datetime.utcnow():
            current_expires = sub_exp

    if current_expires:
        # Stack +30 days on top of current active expiration!
        expires_at = current_expires + timedelta(days=30)
        print(f"🔄 Extending active membership for user {req.internal_id} (Purchase #{purchase_count}) by 30 days until {expires_at.isoformat()}")
    else:
        expires_at = datetime.utcnow() + timedelta(days=30)
        print(f"✅ Activated new 30-day '{req.plan_type}' membership (Purchase #{purchase_count}) for user {req.internal_id}")
    
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
    
    return {"message": f"Payment verified! Subscription extended successfully for 30 days (Total Purchases: {purchase_count})!", "expires_at": expires_at.isoformat(), "purchase_count": purchase_count}

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
        
    hashed_password = pwd_context.hash(req.password)
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
        {"email_or_mobile": identifier_regex}
    ]
    if clean_phone:
        query.append({"phone": clean_phone})
        query.append({"email_or_mobile": clean_phone})
        
    user = users_collection.find_one({"$or": query})
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
        
    if not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
        
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
        return {"linked": True, "can_unlink": True}
        
    time_passed = datetime.utcnow() - linked_at
    can_unlink = time_passed > timedelta(hours=24)
    
    hours_left = 0
    if not can_unlink:
        hours_left = 24 - (time_passed.total_seconds() / 3600)
        
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
        time_passed = datetime.utcnow() - linked_at
        if time_passed < timedelta(hours=24):
            raise HTTPException(status_code=403, detail="Cannot unlink before 24 hours have passed.")
            
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
    ai_server_url = os.getenv("AI_SERVER_URL", "https://ai-script-generator-service.onrender.com").rstrip("/")
    scene_count = max(1, duration // 10)
    word_count = int(duration * 2.5)

    cat_niche = f" in the '{category}' category" if category and str(category).lower() != "random" else ""

    # 1. Primary Attempt: Call External Dedicated Render AI Script Service
    try:
        payload = {
            "topic": topic,
            "category": category,
            "duration_seconds": duration,
            "video_type": video_type,
            "language": language,
            "tone": tone
        }
        
        # Try both /generate-script and /api/generate-ai-script on the external AI service
        for endpoint in ["/generate-script", "/api/generate-ai-script", "/generate"]:
            target_url = f"{ai_server_url}{endpoint}"
            try:
                resp = requests.post(target_url, json=payload, timeout=15)
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
                            
                        print(f"✅ External Render AI Script Service Success ({target_url})!")
                        return {
                            "status": "success",
                            "source": "external_render_ai_service",
                            "topic": topic,
                            "duration_seconds": duration,
                            "video_type": video_type,
                            "language": language,
                            "tone": tone,
                            "estimated_word_count": word_count,
                            "full_script": full_script,
                            "scenes": scenes
                        }
            except Exception as e_inner:
                continue

    except Exception as err_ext:
        print(f"⚠️ External Render AI Service Connection Warning: {err_ext}")

    # 2. Secondary Attempt: Fallback to Gemini AI Direct Key
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            prompt = (
                f"You are a viral AI video script writer. Write a highly engaging {tone} video script about '{topic}' "
                f"in {language} language. Target duration: {duration} seconds (~{word_count} words).\n"
                f"Format requirement: Return ONLY a valid JSON object with:\n"
                f"1. 'full_script': Complete narrative text spoken in video.\n"
                f"2. 'scenes': An array of exactly {scene_count} scene objects, each containing 'text' (1-2 sentences) and 'keyword' (1-2 search terms for background visual clips).\n"
                f"Do not include markdown triple backticks or any conversational text outside JSON."
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
                return {
                    "status": "success",
                    "source": "gemini_ai",
                    "topic": topic,
                    "duration_seconds": duration,
                    "video_type": video_type,
                    "language": language,
                    "tone": tone,
                    "estimated_word_count": word_count,
                    "full_script": parsed.get("full_script", ""),
                    "scenes": parsed.get("scenes", [])
                }
        except Exception as err:
            print(f"⚠️ Gemini API Warning (Falling back to dynamic engine): {err}")

    # Dynamic Smart Script Generator (Zero-Failure Fallback)
    stop_words = {"aur", "ek", "hai", "ki", "ke", "ka", "jo", "se", "me", "ko", "hi", "to", "ye", "wo"}
    keywords = [w.lower() for w in topic.split() if w.isalpha() and w.lower() not in stop_words]
    main_kw = keywords[0] if keywords else topic

    templates = [
        f"Dosto! Kya aapko pata hai {topic} ke baare mein ye hairatangez baatein?",
        f"{topic} ki duniya mein ek aisa raaz hai jisse 90% log bilkul anjaan hain.",
        f"Aaj hum jaanenge {topic} se jude sabse amazing aur secretive facts jo aapka hosh uda denge.",
        f"Aakhir kyun {topic} aaj kal poore internet par itna viral ho raha hai? Aaiye samajhte hain.",
        f"Scientists aur experts bhi {topic} ke is sach ko dekhkar hairan reh gaye hain.",
        f"Agar aap bhi {topic} me interest rakhte hain toh is video ko aakhir tak zaroor dekhein aur follow karein!"
    ]

    scenes = []
    full_text_list = []
    for i in range(scene_count):
        text = templates[i % len(templates)]
        scenes.append({"text": text, "keyword": main_kw})
        full_text_list.append(text)

    return {
        "status": "success",
        "source": "dynamic_ai_engine",
        "topic": topic,
        "duration_seconds": duration,
        "video_type": video_type,
        "language": language,
        "tone": tone,
        "estimated_word_count": word_count,
        "full_script": " ".join(full_text_list),
        "scenes": scenes
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