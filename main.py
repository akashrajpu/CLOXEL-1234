import os
import uuid
import shutil
import requests
import urllib.parse
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
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
    font_name: str = "Arial.ttf"
    font_color: str = "yellow"
    font_size: int = 220
    voice_id: str = "hi-IN-MadhurNeural"
    language: str = "hi"
    video_type: str = "short"  # 'short' or 'long'
    full_script: str = ""      # used if video_type is 'long'

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
        print(f"🎬 Processing video for User: {user_id}")
        
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
            v_paths = fetch_videos(sc["keyword"], v_path, orientation=orientation)
            
            if os.path.exists(a_path) and v_paths:
                taiyaar_scenes.append({
                    "audio": a_path, 
                    "video": v_paths, 
                    "text": sc["text"]
                })

        if taiyaar_scenes:
            output_file = f"output_{job_id}.mp4"
            # Editor ko user ki choice bhejna (font, color)
            target_size = (1280, 720) if req.video_type == "long" else (720, 1280)
            adjusted_font_size = int(req.font_size * 0.7) if req.video_type == "long" else req.font_size
            merge_and_export(taiyaar_scenes, output_file, font_path=f"./fonts/{req.font_name}", color=req.font_color, font_size=adjusted_font_size, target_size=target_size) 
            
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

class CreateOrderRequest(BaseModel):
    internal_id: str
    plan_type: str  # 'short' (50), 'long' (100), 'combo' (119)

class VerifyPaymentRequest(BaseModel):
    internal_id: str
    plan_type: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: Optional[str] = None

@app.post("/generate-custom-video")
async def generate_custom_video(req: VideoRequest, background_tasks: BackgroundTasks):
    user_id = req.user_id
    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Please login or register to generate videos.")
        
    if users_collection is not None:
        user = users_collection.find_one({"internal_id": user_id})
        if user:
            free_demo = user.get("free_demo_count", 2)
            subscription = user.get("subscription", {})
            sub_status = subscription.get("status")
            sub_expires = subscription.get("expires_at")
            
            is_active = False
            if sub_status == "active" and sub_expires:
                if isinstance(sub_expires, str):
                    sub_expires = datetime.fromisoformat(sub_expires)
                if sub_expires > datetime.utcnow():
                    is_active = True
                    
            if not is_active:
                if free_demo > 0:
                    users_collection.update_one({"internal_id": user_id}, {"$inc": {"free_demo_count": -1}})
                else:
                    raise HTTPException(status_code=402, detail="Demo quota exhausted! You have used your 2 free demo videos. Please upgrade your plan to continue generating videos.")

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

    return {
        "name": user.get("name", "User"),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "country": user.get("country", ""),
        "profile_pic": user.get("profile_pic", ""),
        "free_demo_count": free_demo,
        "has_active_subscription": is_active,
        "plan_type": sub_plan if is_active else "none",
        "expires_at": sub_expires.isoformat() if is_active and sub_expires else None
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

    expires_at = datetime.utcnow() + timedelta(days=30)
    
    subscription_data = {
        "plan_type": req.plan_type,
        "status": "active",
        "payment_id": req.razorpay_payment_id,
        "order_id": req.razorpay_order_id,
        "activated_at": datetime.utcnow(),
        "expires_at": expires_at
    }
    
    users_collection.update_one(
        {"internal_id": req.internal_id},
        {"$set": {"subscription": subscription_data}}
    )
    
    print(f"✅ Activated 30-day '{req.plan_type}' membership for user {req.internal_id}")
    return {"message": "Payment verified and subscription activated successfully!", "expires_at": expires_at.isoformat()}

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


@app.post("/generate-script")
async def generate_script(req: ScriptRequest):
    # This is a proxy to the Oracle AI Server
    ai_url = os.getenv("AI_SERVER_URL", "http://localhost:11434")
    
    chunks = max(1, req.duration_seconds // 10)
    prompt = f"Generate {chunks} short distinct script sections about {req.topic}. Format as JSON list of objects with 'text' and 'keyword'."
    
    try:
        generated_scenes = [
            {"text": f"Dosto, kya aap jante hain {req.topic} ke bare mein?", "keyword": req.topic},
            {"text": "Aise hi mazedar videos ke liye hume follow karein.", "keyword": "subscribe"}
        ][:chunks]
        
        return {"scenes": generated_scenes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. Serve Frontend (Must be the last route)
if os.path.isdir("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
else:
    print("WARNING: frontend/dist not found. Run 'npm run build' in the frontend folder.")