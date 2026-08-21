import os
import random
import gc
import warnings
import numpy as np
import textwrap
import subprocess
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, ColorClip, CompositeVideoClip, ImageSequenceClip, VideoClip
from PIL import Image, ImageDraw, ImageFont

warnings.filterwarnings("ignore")

# Pillow 10+ fix
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

def create_animated_text(full_text, size, duration, font_path, highlight_color, font_size=220):
    """
    Ek specific segment ke liye VIRAL STYLE animation banata hai (SUPER BADA TEXT)
    """
    frames = []
    fps = 10
    total_frames = int(duration * fps)
    
    # 1. Text ko Capital kiya taaki aur clear dikhe
    full_text = full_text.upper()
    words = full_text.split()
    
    try:
        font = ImageFont.truetype(font_path, font_size) 
    except:
        print(f"\n⚠️ WARNING: Aapka font '{font_path}' nahi mila! Default 'Arial' use kar raha hu taaki text bada dikhe.")
        try:
            # Agar custom font na mile toh system ka Arial use karega
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Mac users ke liye fallback
            try:
                font = ImageFont.truetype("/Library/Fonts/Arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
                print("❌ ERROR: Koi font nahi mila! Text chhota hi aayega. Please ek sahi .ttf file ./fonts folder mein dalein.")

    # Cache variable to avoid drawing twice per frame (once for RGB, once for mask)
    cache = {'t': -1, 'img': None}

    def get_img(t):
        if cache['t'] == t:
            return cache['img']
            
        i = int(t * fps)
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if not words:
            cache['t'] = t
            cache['img'] = img
            return img
            
        # Current word highlight logic
        word_idx = int((i / total_frames) * len(words))
        if word_idx >= len(words): word_idx = len(words) - 1
        
        # 3. Text ko chunks mein baantna
        is_landscape = size[0] > size[1]
        chunk_size = 8 if is_landscape else 3
        chunk_idx = word_idx // chunk_size
        
        start_idx = chunk_idx * chunk_size
        end_idx = start_idx + chunk_size
        current_chunk_words = words[start_idx:end_idx]
        target_local_idx = word_idx - start_idx
        
        chunk_text = " ".join(current_chunk_words)
        
        # Dynamic text wrap based on screen width
        estimated_char_width = font_size * 0.55
        wrap_width = max(int((size[0] * 0.85) / estimated_char_width), 1)
        wrapped_text = textwrap.fill(chunk_text, width=wrap_width) # Ek line mein words
        lines = wrapped_text.split('\n')
        
        # 4. Spacing ko Font Size ke hisaab se responsive banaya
        line_spacing = int(font_size * 1.15) 
        total_h = len(lines) * line_spacing
        
        if is_landscape:
            y_text = size[1] - total_h - int(size[1] * 0.1) # Bottom se 10% upar
        else:
            y_text = (size[1] - total_h) / 2 # Center screen
        
        local_word_count = 0
        shadow_offset = max(4, int(font_size * 0.04))
        
        for line in lines:
            line_words = line.split()
            # Bounding box logic
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            current_x = (size[0] - line_width) / 2
            
            for word in line_words:
                color = highlight_color if local_word_count <= target_local_idx else "white" 
                
                # Shadow aur Text draw karna
                draw.text((current_x + shadow_offset, y_text + shadow_offset), word, font=font, fill=(0,0,0,255)) # Dark Shadow
                draw.text((current_x, y_text), word, font=font, fill=color)
                
                # Agle word ki X position
                word_bbox = draw.textbbox((0, 0), word + " ", font=font)
                current_x += (word_bbox[2] - word_bbox[0])
                local_word_count += 1
                
            # Agli line ki Y position
            y_text += line_spacing 
            
        cache['t'] = t
        cache['img'] = img
        return img
        
    def make_frame(t):
        return np.array(get_img(t).convert('RGB'))
        
    def make_mask(t):
        return np.array(get_img(t).split()[3]) / 255.0
    
    clip = VideoClip(make_frame, duration=duration).set_fps(fps)
    mask_clip = VideoClip(make_mask, ismask=True, duration=duration).set_fps(fps)
    return clip.set_mask(mask_clip)
    
def merge_and_export(scene_list, output_name, font_path="./fonts/Arial.ttf", color="#FFEE00", font_size=220, target_size=(1080, 1920), bg_music="cool.mp3"):
    """
    Har scene ka apna audio, apna video, aur apni text script merge karta hai.
    Saves RAM by rendering individual lightweight scenes and concatenating via raw FFmpeg.
    """
    print(f"\n🎸 Rendering {len(scene_list)} scenes individually to save RAM (Size: {target_size})...")
    
    temp_scene_files = []
    job_dir = os.path.dirname(output_name) if os.path.dirname(output_name) else "."

    for i, scene in enumerate(scene_list):
        video_path = scene['video'][0] if isinstance(scene['video'], list) else scene['video']
        audio_path = scene['audio']
        
        # Audio clip
        a_clip = AudioFileClip(audio_path)
        clip_duration = a_clip.duration
        
        # Video/Image clip load with fail-safe fallback
        is_image = str(video_path).lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
        
        try:
            if is_image and os.path.exists(video_path):
                v_clip = ImageClip(video_path).resize(height=target_size[1])
            elif os.path.exists(video_path):
                v_clip = VideoFileClip(video_path, audio=False).resize(height=target_size[1])
            else:
                print(f"⚠️ Media file missing ({video_path}), using ColorClip background fallback...")
                v_clip = ColorClip(size=target_size, color=(15, 10, 35))
        except Exception as e_clip:
            print(f"⚠️ Media load error ({video_path}): {e_clip}. Using solid color fallback...")
            v_clip = ColorClip(size=target_size, color=(15, 10, 35))

        if v_clip.w > target_size[0]:
            v_clip = v_clip.crop(x_center=v_clip.w/2, width=target_size[0])
        elif v_clip.w < target_size[0]:
            v_clip = v_clip.resize(width=target_size[0])
            v_clip = v_clip.crop(y_center=v_clip.h/2, height=target_size[1])
            
        v_clip = v_clip.set_duration(clip_duration)
        v_clip = v_clip.set_audio(a_clip)

        # Text clip
        clip_text_segment = scene['text']
        txt_clip = create_animated_text(clip_text_segment, target_size, clip_duration, font_path, color, font_size)
        
        scene_combined = CompositeVideoClip([v_clip, txt_clip.set_position('center')])
        
        # Render scene individually to disk to free RAM immediately
        scene_output = os.path.join(job_dir, f"temp_rendered_scene_{i}.mp4")
        print(f"🎬 Rendering Scene {i+1}/{len(scene_list)} to {scene_output}...")
        scene_combined.write_videofile(scene_output, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=1, logger=None)
        
        # Immediate Cleanup to prevent OOM
        scene_combined.close()
        v_clip.close()
        a_clip.close()
        txt_clip.close()
        del scene_combined, v_clip, a_clip, txt_clip
        gc.collect()
        
        temp_scene_files.append(scene_output)

    # Load rendered lightweight clips using RAW FFMPEG (Zero RAM)
    print(f"🔗 Concatenating {len(temp_scene_files)} scenes via ffmpeg...")
    list_path = os.path.join(job_dir, "concat_list.txt")
    with open(list_path, "w") as f:
        for tf in temp_scene_files:
            f.write(f"file '{tf}'\n")
            
    temp_merged = os.path.join(job_dir, "temp_merged_final.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", temp_merged], check=True)

    # Background Music Selection Logic
    bg_music_file = None
    if bg_music and str(bg_music).lower() != "none":
        if os.path.exists(bg_music):
            bg_music_file = bg_music
        elif os.path.exists(os.path.join(".", bg_music)):
            bg_music_file = os.path.join(".", bg_music)
        else:
            search_dirs = [".", "./songs", "./songs copy"]
            possible = []
            for d in search_dirs:
                if os.path.exists(d):
                    found = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(('.mp3', '.wav'))]
                    possible.extend(found)
            
            if possible:
                if str(bg_music).lower() == "random":
                    bg_music_file = random.choice(possible)
                else:
                    for p in possible:
                        if os.path.basename(p).lower() == str(bg_music).lower():
                            bg_music_file = p
                            break
                    if not bg_music_file:
                        bg_music_file = possible[0]

    if bg_music_file and os.path.exists(bg_music_file):
        print(f"🎬 Adding selected background music: {bg_music_file}...")
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_merged,
            "-i", bg_music_file,
            "-filter_complex", "[1:a]volume=0.12[a1];[0:a][a1]amix=inputs=2:duration=first[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            output_name
        ]
        subprocess.run(cmd, check=True)
        if os.path.exists(temp_merged): os.remove(temp_merged)
    else:
        print("🎬 No background music selected or file not found. Exporting final video...")
        if os.path.exists(temp_merged): os.rename(temp_merged, output_name)
    
    # Final Cleanup
    if os.path.exists(list_path): os.remove(list_path)
    for f in temp_scene_files: 
        if os.path.exists(f): os.remove(f)
    
    return output_name