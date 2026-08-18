import os
import uuid
import shutil
import requests
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
    email_or_mobile: str
    password: str

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
                    videos_collection.insert_one({
                        "internal_id": req.user_id,
                        "job_id": job_id,
                        "topic": req.topic,
                        "cloudinary_url": cloudinary_url,
                        "created_at": datetime.utcnow()
                    })
                except Exception as e:
                    print(f"❌ Failed to save video history to DB: {e}")
        else:
            jobs[job_id] = {"status": "failed", "error": "No scenes ready"}

    except Exception as e:
        print(f"❌ Error in full_process: {e}")
        jobs[job_id] = {"status": "failed", "error": str(e)}

@app.post("/generate-custom-video")
async def generate_custom_video(req: VideoRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "user_id": req.user_id}
    background_tasks.add_task(full_process, req, job_id)
    return {"job_id": job_id, "status": "Processing Started"}

@app.post("/register")
async def register_user(req: UserRegister):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    existing_user = users_collection.find_one({"email_or_mobile": req.email_or_mobile})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
        
    hashed_password = pwd_context.hash(req.password)
    internal_id = str(uuid.uuid4())
    
    new_user = {
        "email_or_mobile": req.email_or_mobile,
        "password_hash": hashed_password,
        "internal_id": internal_id
    }
    
    users_collection.insert_one(new_user)
    return {"message": "User registered successfully", "internal_id": internal_id}

@app.post("/login")
async def login_user(req: UserLogin):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    user = users_collection.find_one({"email_or_mobile": req.email_or_mobile})
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
        return FileResponse(job["file"], media_type="video/mp4", filename="zobbly_reel.mp4")
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
    flow = get_youtube_flow()
    if not flow:
        raise HTTPException(status_code=500, detail="YouTube Client ID/Secret not configured in environment.")
    
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=internal_id
    )
    return {"auth_url": auth_url}

@app.get("/youtube/callback")
async def youtube_callback(state: str, code: str):
    internal_id = state
    flow = get_youtube_flow()
    if not flow:
        raise HTTPException(status_code=500, detail="YouTube Client ID/Secret not configured.")
    
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    creds_dict = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
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