import os
import re
import time
import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def generate_gemini_cartoon_animation(user_prompt: str, output_mp4: str, duration: float = 5.0, target_size: tuple = (1280, 720), fps: int = 20) -> str:
    """
    Generates a frame-by-frame 2D Cartoon / Anime Animation MP4 video using Gemini AI code generation.
    Used for Ultra Mode when Category is 'Cartoon' or 'Animation'.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("AI_API_KEY")
    if not api_key:
        print("⚠️ GEMINI_API_KEY / GOOGLE_API_KEY environment variable not set. Skipping AI animation generation.")
        return None

    w, h = target_size
    total_frames = max(20, int(duration * fps))

    system_instruction = f"""
    You are an expert Python Developer, Animator, and Cartoon Director. 
    Read the following scene story and generate a COMPLETE, ERROR-FREE Python script to create a 2D Cartoon/Animation video.
    
    STRICT RULES FOR YOUR CODE:
    1. Output ONLY raw, runnable Python code. DO NOT wrap it in markdown block quotes like ```python ... ```. Do not add any text explanations.
    2. IMPORT THESE EXACT MODULES:
       from PIL import Image, ImageDraw, ImageFont
       import math
       import imageio
       import numpy as np
       
    3. SCENE & CHARACTER ANIMATION:
       - Canvas size MUST be {w}x{h}. Total frames to generate: {total_frames}.
       - Create a list named `frames = []`.
       - Loop through frame index `for frame_idx in range({total_frames}):`
       - For each frame, create a PIL Image: `img = Image.new('RGB', ({w}, {h}), (25, 25, 45))`
       - Draw colorful cartoon backgrounds, landscapes, sky/nature, or indoor rooms.
       - Draw expressively animated cartoon characters, stick figures, animals, or objects that move smoothly across frames.
       - Calculate dynamic movement using `frame_idx` (e.g. `pos_x = int(50 + frame_idx * 5)`).
       
    4. VERY IMPORTANT MATH RULE: All coordinates (x, y) passed to ImageDraw functions MUST be integers using int(). No floats.
       e.g., draw.ellipse((int(x), int(y), int(x+40), int(y+40)), fill=(255, 200, 100))
    
    5. MP4 SAVING RULE: Store all generated PIL Images in `frames`. At the end of the script, save them as an MP4 exactly like this:
       writer = imageio.get_writer('{output_mp4}', fps={fps})
       for img in frames:
           writer.append_data(np.array(img.convert('RGB')))
       writer.close()

    6. Put everything directly in the global scope (do not wrap in a main function).
    
    Scene Story: "{user_prompt}"
    """

    print(f"🎬 [Gemini Cartoon Engine] Generating AI Animation Code for scene: '{user_prompt[:60]}...' ({total_frames} frames)...")
    
    generated_code = ""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"   🤖 Calling Gemini API (attempt {attempt+1}/{max_retries})...")
            # Try new google-genai SDK first
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=system_instruction,
                )
                generated_code = response.text
            except Exception as e_new_sdk:
                # Try legacy google.generativeai SDK second
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=api_key)
                    g_model = legacy_genai.GenerativeModel('gemini-1.5-flash')
                    res_legacy = g_model.generate_content(system_instruction)
                    generated_code = res_legacy.text
                except Exception as e_leg_sdk:
                    # Direct REST API fallback third (100% dependency-free)
                    import requests
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                    payload = {"contents": [{"parts": [{"text": system_instruction}]}]}
                    r_rest = requests.post(url, json=payload, timeout=30)
                    r_data = r_rest.json()
                    candidates = r_data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            generated_code = parts[0].get("text", "")

            if generated_code:
                print(f"   ✅ Gemini API returned code ({len(generated_code)} chars)")
                break
        except Exception as api_err:
            print(f"⚠️ Gemini Animation API attempt {attempt+1}/{max_retries} warning: {api_err}")
            if "503" in str(api_err) or "429" in str(api_err):
                time.sleep(2)
            else:
                break

    if not generated_code:
        return None

    # Code Cleaning
    clean_code = re.sub(r"^```python\n?", "", generated_code, flags=re.MULTILINE)
    clean_code = re.sub(r"^```\n?", "", clean_code, flags=re.MULTILINE)
    clean_code = clean_code.strip()

    exec_globals = {
        "Image": Image,
        "ImageDraw": ImageDraw,
        "ImageFont": ImageFont,
        "math": __import__("math"),
        "imageio": imageio,
        "np": np,
        "os": os
    }

    try:
        print(f"   ⚙️ Executing Gemini generated Python animation code...")
        exec(clean_code, exec_globals)
        if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
            print(f"🎉 [Gemini Cartoon Engine] Successfully rendered AI Cartoon MP4: {output_mp4}")
            return output_mp4
        else:
            print(f"⚠️ [Gemini Cartoon Engine] Output MP4 missing or 0 bytes: {output_mp4}")
    except Exception as exec_err:
        import traceback
        print(f"❌ [Gemini Cartoon Engine] Execution Error: {exec_err}")
        traceback.print_exc()

    return None
