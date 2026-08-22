import requests
import os

# === APNI PEXELS KEY YAHAN DAALO ===
PEXELS_API_KEY = "jqGZN1a4uHQFpxqdFAdVaD1l1eyjW1kzHqtdlNJ1TPkSmOEXcbAL7yhN"

def fetch_videos(keyword, job_id, count=1, orientation="portrait"):
    """
    Ek se zyada videos download karne ke liye logic
    """
    print(f"📥 Pexels se '{keyword}' ke liye {count} clips ({orientation}) dhoondhi ja rahi hain...")
    headers = {"Authorization": PEXELS_API_KEY}
    
    # Per_page mein hum 'count' bhej rahe hain
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page={count}&orientation={orientation}"
    
    try:
        response = requests.get(url, headers=headers).json()
        video_paths = []
        
        if 'videos' in response and len(response['videos']) > 0:
            for i, video_data in enumerate(response['videos']):
                # Find the best resolution (around 720p to save RAM, avoid 4K)
                valid_files = [vf for vf in video_data['video_files'] if vf.get('link')]
                valid_files.sort(key=lambda x: x.get('width', 0) * x.get('height', 0))
                
                best_file = valid_files[0] if valid_files else None
                for vf in valid_files:
                    if vf.get('height', 0) >= 720 and vf.get('height', 0) <= 1080:
                        best_file = vf
                        break
                
                if not best_file:
                    continue
                    
                video_url = best_file['link']
                dir_name = os.path.dirname(job_id)
                base_name = os.path.basename(job_id)
                if dir_name:
                    filename = os.path.join(dir_name, f"clip_{base_name}_{i}.mp4")
                else:
                    filename = f"clip_{base_name}_{i}.mp4"
                
                print(f"✅ Clip {i+1} mil gayi! Downloading...")
                vid_data = requests.get(video_url).content
                with open(filename, "wb") as f:
                    f.write(vid_data)
                video_paths.append(filename)
                
            return video_paths
        else:
            print(f"⚠️ Warning: '{keyword}' ke liye videos nahi mili.")
            return []
            
    except Exception as e:
        print(f"❌ Network Error: {e}")
        return []