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
    Auto-fitting, non-overflowing subtitle renderer with ultra-fast execution and zero memory leaks.
    """
    frames = []
    fps = 10
    total_frames = max(int(duration * fps), 1)
    
    full_text = full_text.upper().strip()
    words = full_text.split()
    
    # Base Target Font Size calculation based on screen dimensions
    target_width = int(size[0] * 0.86) # 86% screen margin
    max_font_size = int(size[1] * 0.08) if size[0] > size[1] else int(size[0] * 0.09) # Smart responsive size
    user_font_size = min(font_size, max_font_size) if font_size > 50 else max_font_size

    def load_font(fs):
        try:
            return ImageFont.truetype(font_path, fs)
        except Exception:
            try:
                return ImageFont.truetype("arial.ttf", fs)
            except Exception:
                try:
                    return ImageFont.truetype("/Library/Fonts/Arial.ttf", fs)
                except Exception:
                    return ImageFont.load_default()

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
            
        word_idx = int((i / total_frames) * len(words))
        if word_idx >= len(words): word_idx = len(words) - 1
        
        is_landscape = size[0] > size[1]
        chunk_size = 6 if is_landscape else 3
        chunk_idx = word_idx // chunk_size
        
        start_idx = chunk_idx * chunk_size
        end_idx = start_idx + chunk_size
        current_chunk_words = words[start_idx:end_idx]
        target_local_idx = word_idx - start_idx
        
        # Determine optimal font size so NO word/line overflows screen
        active_font = load_font(user_font_size)
        
        lines = []
        curr_line = []
        for w in current_chunk_words:
            test_line = " ".join(curr_line + [w])
            bbox = draw.textbbox((0, 0), test_line, font=active_font)
            if (bbox[2] - bbox[0]) <= target_width or not curr_line:
                curr_line.append(w)
            else:
                lines.append(curr_line)
                curr_line = [w]
        if curr_line:
            lines.append(curr_line)

        # Scale down font size if any line is still too wide for long custom font words
        for line_words in lines:
            line_str = " ".join(line_words)
            bbox = draw.textbbox((0, 0), line_str, font=active_font)
            line_w = bbox[2] - bbox[0]
            if line_w > target_width:
                scaled_fs = max(int(user_font_size * (target_width / line_w)), 24)
                active_font = load_font(scaled_fs)
                break

        line_spacing = int(active_font.size * 1.2)
        total_h = len(lines) * line_spacing
        
        if is_landscape:
            y_text = size[1] - total_h - int(size[1] * 0.12)
        else:
            y_text = (size[1] - total_h) / 2
        
        local_word_count = 0
        shadow_offset = max(3, int(active_font.size * 0.04))
        
        for line_words in lines:
            # Measure complete line width for center alignment
            space_bbox = draw.textbbox((0, 0), " ", font=active_font)
            space_w = space_bbox[2] - space_bbox[0]
            
            line_total_w = sum((draw.textbbox((0, 0), w, font=active_font)[2] - draw.textbbox((0, 0), w, font=active_font)[0]) for w in line_words) + space_w * (len(line_words) - 1)
            current_x = (size[0] - line_total_w) / 2
            
            for w in line_words:
                color = highlight_color if local_word_count <= target_local_idx else "white"
                
                # Draw high-contrast text outline & drop shadow (No screen overflow)
                draw.text((current_x + shadow_offset, y_text + shadow_offset), w, font=active_font, fill=(0, 0, 0, 240))
                draw.text((current_x, y_text), w, font=active_font, fill=color)
                
                w_bbox = draw.textbbox((0, 0), w, font=active_font)
                w_w = w_bbox[2] - w_bbox[0]
                current_x += w_w + space_w
                local_word_count += 1
                
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
        
        # Render scene individually to disk with ultrafast preset & low thread overhead
        scene_output = os.path.join(job_dir, f"temp_rendered_scene_{i}.mp4")
        print(f"🎬 [Fast-Render] Scene {i+1}/{len(scene_list)} -> {scene_output}...")
        scene_combined.write_videofile(
            scene_output, 
            codec="libx264", 
            audio_codec="aac", 
            fps=20, 
            preset="ultrafast", 
            threads=2, 
            ffmpeg_params=["-crf", "26", "-pix_fmt", "yuv420p"],
            logger=None
        )
        
        # Immediate Cleanup & Garbage Collection to prevent Render 512MB RAM crash
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