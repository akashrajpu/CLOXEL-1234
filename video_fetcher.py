import requests
import os

# === MULTI-PROVIDER ENVIRONMENT VARIABLES ===
# Render Environment Variables:
# - PEXELS_API_KEY
# - PIXABAY_API_KEY
# - UNSPLASH_ACCESS_KEY
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "jqGZN1a4uHQFpxqdFAdVaD1l1eyjW1kzHqtdlNJ1TPkSmOEXcbAL7yhN")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

def fetch_pexels_videos(keyword, job_id, count=1, orientation="portrait"):
    """Pexels API se HD stock video clips download karta hai"""
    key = os.getenv("PEXELS_API_KEY") or PEXELS_API_KEY
    if not key:
        return []
        
    print(f"📥 [Pexels] '{keyword}' ke liye video clip ({orientation}) dhoondh rahe hain...")
    headers = {"Authorization": key}
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page={count}&orientation={orientation}"
    
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code != 200:
            return []
        data = res.json()
        video_paths = []
        if 'videos' in data and len(data['videos']) > 0:
            for i, video_data in enumerate(data['videos']):
                valid_files = [vf for vf in video_data.get('video_files', []) if vf.get('link')]
                if not valid_files: continue
                valid_files.sort(key=lambda x: x.get('width', 0) * x.get('height', 0))
                best_file = valid_files[0]
                for vf in valid_files:
                    if 720 <= vf.get('height', 0) <= 1080:
                        best_file = vf
                        break
                video_url = best_file['link']
                dir_name = os.path.dirname(job_id)
                base_name = os.path.basename(job_id)
                filename = os.path.join(dir_name, f"clip_{base_name}_{i}.mp4") if dir_name else f"clip_{base_name}_{i}.mp4"
                
                vid_data = requests.get(video_url, timeout=15).content
                with open(filename, "wb") as f:
                    f.write(vid_data)
                video_paths.append(filename)
                print(f"✅ [Pexels] Video clip downloaded: {filename}")
            return video_paths
    except Exception as e:
        print(f"⚠️ [Pexels] Error: {e}")
    return []

def fetch_pixabay_videos(keyword, job_id, count=1, orientation="portrait"):
    """Pixabay API se free HD stock videos download karta hai"""
    key = os.getenv("PIXABAY_API_KEY") or PIXABAY_API_KEY
    if not key:
        return []
        
    print(f"📥 [Pixabay] '{keyword}' ke liye video clip ({orientation}) dhoondh rahe hain...")
    v_type = "film" if orientation == "landscape" else "all"
    url = f"https://pixabay.com/api/videos/?key={key}&q={requests.utils.quote(keyword)}&video_type={v_type}&per_page=5"
    
    try:
        res = requests.get(url, timeout=12)
        if res.status_code != 200:
            return []
        data = res.json()
        video_paths = []
        hits = data.get('hits', [])
        if hits:
            for i, hit in enumerate(hits[:count]):
                videos = hit.get('videos', {})
                best_vid = videos.get('medium') or videos.get('large') or videos.get('small')
                if not best_vid or not best_vid.get('url'): continue
                video_url = best_vid['url']
                dir_name = os.path.dirname(job_id)
                base_name = os.path.basename(job_id)
                filename = os.path.join(dir_name, f"pixabay_{base_name}_{i}.mp4") if dir_name else f"pixabay_{base_name}_{i}.mp4"
                
                vid_data = requests.get(video_url, timeout=15).content
                with open(filename, "wb") as f:
                    f.write(vid_data)
                video_paths.append(filename)
                print(f"✅ [Pixabay] Video clip downloaded: {filename}")
            return video_paths
    except Exception as e:
        print(f"⚠️ [Pixabay] Error: {e}")
    return []

def fetch_videos(keyword, job_id, count=1, orientation="portrait"):
    """
    Multi-Provider Stock Video Fetcher:
    1. Primary: Pexels Video API (PEXELS_API_KEY)
    2. Fallback 1: Pixabay Video API (PIXABAY_API_KEY)
    3. Fallback 2: General Keyword Retry ('nature', 'technology', 'city')
    """
    # 1. Primary: Try Pexels Video Search
    clips = fetch_pexels_videos(keyword, job_id, count=count, orientation=orientation)
    if clips:
        return clips
        
    # 2. Fallback 1: Try Pixabay Video Search
    clips = fetch_pixabay_videos(keyword, job_id, count=count, orientation=orientation)
    if clips:
        return clips

    # 3. Fallback 2: Retry Pexels with generic safe keywords
    for fallback_kw in ["nature", "technology", "abstract", "city"]:
        if fallback_kw != keyword.lower():
            print(f"🔄 Retrying with fallback keyword: '{fallback_kw}'...")
            clips = fetch_pexels_videos(fallback_kw, job_id, count=count, orientation=orientation)
            if clips:
                return clips
                
    print(f"❌ No videos found for '{keyword}' across all API providers.")
    return []