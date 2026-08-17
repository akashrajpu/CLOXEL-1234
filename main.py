import os
import uuid
import shutil
import requests
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

# Aapke modules
from video_editor import merge_and_export
from audio_engine import make_audio
from video_fetcher import fetch_videos

load_dotenv("config.env")

cloudinary.config( 
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'), 
  api_key = os.getenv('CLOUDINARY_API_KEY'), 
  api_secret = os.getenv('CLOUDINARY_API_SECRET') 
)

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

class VideoRequest(BaseModel):
    scenes: List[Scene] = []
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
            target_size = (1920, 1080) if req.video_type == "long" else (1080, 1920)
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
        else:
            jobs[job_id] = {"status": "failed", "error": "No scenes ready"}

    except Exception as e:
        print(f"❌ Error in full_process: {e}")
        jobs[job_id] = {"status": "failed", "error": str(e)}

@app.post("/generate-custom-video")
async def generate_custom_video(req: VideoRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing"}
    background_tasks.add_task(full_process, req, job_id)
    return {"job_id": job_id, "status": "Processing Started"}

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

@app.post("/generate-script")
async def generate_script(req: ScriptRequest):
    # This is a proxy to the Oracle AI Server
    ai_url = os.getenv("AI_SERVER_URL", "http://localhost:11434")
    
    # Calculate how many chunks based on duration (e.g. 1 chunk per 10 seconds)
    chunks = max(1, req.duration_seconds // 10)
    
    # Dummy logic to be replaced with real Ollama/Omana integration
    prompt = f"Generate {chunks} short distinct script sections about {req.topic}. Format as JSON list of objects with 'text' and 'keyword'."
    
    try:
        # Example call to Ollama generate endpoint
        # resp = requests.post(f"{ai_url}/api/generate", json={"model": "llama3", "prompt": prompt, "stream": False})
        
        # Fake response for now
        generated_scenes = [
            {"text": f"Dosto, kya aap jante hain {req.topic} ke bare mein?", "keyword": req.topic},
            {"text": "Aise hi mazedar videos ke liye hume follow karein.", "keyword": "subscribe"}
        ][:chunks]
        
        return {"scenes": generated_scenes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))