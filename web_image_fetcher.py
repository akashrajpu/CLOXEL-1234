"""
Web Image Downloader Helper (Polished & Resilient)
Downloads high-resolution web images for any character or scene query.
"""

import requests
import urllib.parse
import os
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_web_image(query: str, save_path: str) -> bool:
    """
    Searches and downloads a high-resolution image for any topic/character query using Google Images, Unsplash, Wikimedia & Pollinations AI.
    """
    print(f"🔎 [Web Image Search Engine] Searching Google & Web for: '{query}'...")
    
    # 1. Google Images Scraping (Direct HD Web Images)
    try:
        clean_q = urllib.parse.quote(f"{query} HD wallpaper photo")
        google_url = f"https://www.google.com/search?q={clean_q}&tbm=isch"
        res = requests.get(google_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            import re
            # Extract direct image URLs from Google Search HTML
            img_urls = re.findall(r'https?://[^"\s]+\.(?:jpg|jpeg|png|webp)', res.text, re.IGNORECASE)
            valid_urls = [u for u in img_urls if "gstatic" not in u and "google" not in u]
            if not valid_urls:
                valid_urls = img_urls
            
            for img_url in valid_urls[:5]:
                try:
                    img_req = requests.get(img_url, headers=HEADERS, timeout=8)
                    if img_req.status_code == 200 and len(img_req.content) > 20000:
                        with open(save_path, "wb") as f:
                            f.write(img_req.content)
                        print(f"✅ [Google Images HD] Successfully downloaded: {save_path}")
                        return True
                except Exception:
                    continue
    except Exception as e_g:
        print(f"⚠️ Google Images search skip: {e_g}")

    # 2. Unsplash Source Engine (High-Resolution Stock Photos)
    try:
        unsplash_url = f"https://source.unsplash.com/1600x900/?{urllib.parse.quote(query)}"
        u_res = requests.get(unsplash_url, headers=HEADERS, timeout=8)
        if u_res.status_code == 200 and len(u_res.content) > 30000:
            with open(save_path, "wb") as f:
                f.write(u_res.content)
            print(f"✅ [Unsplash HD Engine] Successfully downloaded: {save_path}")
            return True
    except Exception as e_u:
        print(f"⚠️ Unsplash search skip: {e_u}")

    # 3. Try Wikimedia Commons API
    try:
        wiki_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(query)}&gsrlimit=5&prop=imageinfo&iiprop=url&format=json"
        res = requests.get(wiki_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            pages = res.json().get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                imageinfo = page_data.get("imageinfo", [])
                if imageinfo and imageinfo[0].get("url"):
                    img_url = imageinfo[0]["url"]
                    if img_url.lower().endswith(('.jpg', '.png', '.jpeg', '.webp')):
                        img_data = requests.get(img_url, headers=HEADERS, timeout=10).content
                        if len(img_data) > 15000:
                            with open(save_path, "wb") as f:
                                f.write(img_data)
                            print(f"✅ [Wikimedia] Downloaded image: {save_path}")
                            return True
    except Exception as e_w:
        print(f"⚠️ Wikimedia search skip: {e_w}")

    # 4. Try Pollinations Free AI Image Generator (If no web search result found, generate exact HD image!)
    try:
        print(f"🎨 [AI Generator Fallback] Generating exact HD image for: '{query}'...")
        prompt_str = urllib.parse.quote(f"high quality realistic photo of {query}, 8k resolution, cinematic lighting, wallpaper")
        poll_url = f"https://image.pollinations.ai/prompt/{prompt_str}?width=1280&height=720&nologo=true"
        img_data = requests.get(poll_url, headers=HEADERS, timeout=12).content
        if len(img_data) > 15000:
            with open(save_path, "wb") as f:
                f.write(img_data)
            print(f"✅ [Pollinations AI Engine] Generated exact HD image: {save_path}")
            return True
    except Exception as e_p:
        print(f"⚠️ Pollinations search skip: {e_p}")

    return False

if __name__ == "__main__":
    fetch_web_image("Karna Mahabharata warrior", "test_karna_warrior.jpg")
