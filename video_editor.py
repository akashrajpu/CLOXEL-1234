"""
=============================================================================
PRO DYNAMIC SCENE & MULTI-CHARACTER ULTRA VIDEO EDITOR
=============================================================================
Description: Advanced video editor supporting:
  1. Script-driven Dynamic Multi-Character Cutout Overlay (Left / Right / Center).
  2. Selective Background Removal (Remove BG ONLY for dialogue characters, keep full BG for scene backdrop).
  3. Dynamic Auto-Positioning Subtitles & Color Animations (Top, Center, Bottom, Rainbow/Gold/White).
  4. Web & AI Character Photo Fetching.
=============================================================================
"""

import os
import math
import random
import gc
import warnings
import numpy as np
import textwrap
import subprocess
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, ColorClip, CompositeVideoClip, VideoClip
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        from moviepy.video.VideoClip import ImageClip, ColorClip, VideoClip
        from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    except ImportError:
        from moviepy import VideoFileClip, AudioFileClip, ImageClip, ColorClip, CompositeVideoClip, VideoClip
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

warnings.filterwarnings("ignore")

# Pillow 10+ fix
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

try:
    from bg_remover import remove_background
except ImportError:
    remove_background = None

try:
    from web_image_fetcher import fetch_web_image
except ImportError:
    fetch_web_image = None


# =============================================================================
# Subtitle Color Palette & Random Dynamic Position Generator
# =============================================================================
COLOR_PALETTES = [
    "#FFEE00", # Vivid Yellow
    "#00FFFF", # Neon Cyan
    "#FF0055", # Hot Pink
    "#00FF66", # Electric Green
    "#FF9900", # Deep Amber
    "#FFFFFF"  # Pure White
]

POSITIONS = ["center", "bottom", "top"]


def create_dynamic_animated_text(
    full_text: str,
    size: tuple,
    duration: float,
    font_path: str,
    font_size: int = 220,
    text_position: str = "random",
    text_color: str = "random"
):
    """
    Renders subtitles with dynamic random positions (Top / Center / Bottom) and 
    colorful highlight animations (Yellow / Cyan / Pink / Green / Amber) across scenes.
    """
    fps = 10
    total_frames = max(int(duration * fps), 1)
    
    has_devanagari = any('\u0900' <= char <= '\u097F' for char in full_text)
    if not has_devanagari:
        full_text = full_text.upper().strip()
    else:
        full_text = full_text.strip()
        
    words = full_text.split()
    
    target_width = int(size[0] * 0.86)
    max_font_size = int(size[1] * 0.08) if size[0] > size[1] else int(size[0] * 0.09)
    user_font_size = min(font_size, max_font_size) if font_size > 50 else max_font_size

    # Choose random color & position per scene if specified
    highlight_color = random.choice(COLOR_PALETTES) if text_color == "random" else text_color
    chosen_pos = random.choice(POSITIONS) if text_position == "random" else text_position

    def load_font(fs):
        devanagari_font_candidates = [
            "./fonts/NotoSansDevanagari-Bold.ttf",
            "./fonts/NotoSansDevanagari-Regular.ttf",
            "/System/Library/Fonts/Supplemental/ITFDevanagari.ttc",
            "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
            "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
        ]
        
        if has_devanagari:
            for df_path in devanagari_font_candidates:
                if os.path.exists(df_path):
                    try:
                        return ImageFont.truetype(df_path, fs)
                    except Exception:
                        pass
                        
        try:
            return ImageFont.truetype(font_path, fs)
        except Exception:
            pass

        fallback_candidates = devanagari_font_candidates + [
            "arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf"
        ]
        for font_candidate in fallback_candidates:
            if os.path.exists(font_candidate):
                try:
                    return ImageFont.truetype(font_candidate, fs)
                except Exception:
                    pass
                    
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
        
        # Calculate Y-position based on chosen_pos
        if chosen_pos == "top":
            y_text = int(size[1] * 0.12)
        elif chosen_pos == "bottom":
            y_text = size[1] - total_h - int(size[1] * 0.12)
        else: # center
            y_text = (size[1] - total_h) / 2
        
        local_word_count = 0
        shadow_offset = max(3, int(active_font.size * 0.04))
        
        for line_words in lines:
            space_bbox = draw.textbbox((0, 0), " ", font=active_font)
            space_w = space_bbox[2] - space_bbox[0]
            
            line_total_w = sum((draw.textbbox((0, 0), w, font=active_font)[2] - draw.textbbox((0, 0), w, font=active_font)[0]) for w in line_words) + space_w * (len(line_words) - 1)
            current_x = (size[0] - line_total_w) / 2
            
            for w in line_words:
                color = highlight_color if local_word_count <= target_local_idx else "white"
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


# =============================================================================
# Multi-Character Ultra Scene Canvas Generator
# =============================================================================
def create_multi_character_ultra_clip(
    scene_info: dict,
    duration: float,
    size: tuple = (1920, 1080),
    fps: int = 20
) -> VideoClip:
    """
    Creates a Multi-Character Ultra Scene:
      - 1 Full Backdrop Image (Background intact, NO BG removal).
      - Selective Dialogue Characters Cutout (BG removed for characters like Karna, Angad, Arjuna).
      - Character Auto-Positioning (Left / Right / Center side by side).
    """
    w, h = size
    bg_img_path = scene_info.get("background_image") or scene_info.get("video")
    char_list = scene_info.get("characters", []) # List of dicts: [{"name": "Karna", "image": "...", "pos": "left"}]
    
    # 1. Load Background Backdrop Canvas (Intact, NO BG Removal)
    if bg_img_path and os.path.exists(bg_img_path):
        bg_pil = Image.open(bg_img_path).convert("RGBA").resize(size, Image.LANCZOS)
    else:
        # Fallback dark epic background
        bg_pil = Image.new("RGBA", size, (25, 18, 12, 255))
        
    # 2. Process Dialogue Character Cutouts (Selective BG Removal)
    processed_chars = []
    
    for idx, c_info in enumerate(char_list):
        c_path = c_info.get("image")
        c_pos = c_info.get("pos", "left" if idx % 2 == 0 else "right")
        
        if c_path and os.path.exists(c_path):
            char_pil = Image.open(c_path).convert("RGBA")
            # Selectively Remove BG for dialogue character
            if remove_background:
                fg_cutout = remove_background(char_pil)
            else:
                fg_cutout = char_pil
                
            # Resize character to ~80% height of canvas
            target_h = int(h * 0.82)
            aspect = fg_cutout.width / fg_cutout.height
            target_w = int(target_h * aspect)
            fg_resized = fg_cutout.resize((target_w, target_h), Image.LANCZOS)
            
            # Position character (Left / Right / Center)
            if c_pos == "left":
                pos_x = int(w * 0.04)
            elif c_pos == "right":
                pos_x = w - target_w - int(w * 0.04)
            else: # center
                pos_x = (w - target_w) // 2
                
            pos_y = h - target_h
            processed_chars.append({"img": fg_resized, "x": pos_x, "y": pos_y, "pos": c_pos})

    # 3. Frame generator with subtle motion (Ken Burns BG + Floating Characters)
    def get_frame(t):
        progress = t / duration if duration > 0 else 0
        
        # Background slow zoom (1.0 -> 1.06)
        bg_scale = 1.0 + (0.06 * progress)
        bg_w_s = int(w * bg_scale)
        bg_h_s = int(h * bg_scale)
        bg_s = bg_pil.resize((bg_w_s, bg_h_s), Image.BILINEAR)
        
        crop_x = (bg_w_s - w) // 2
        crop_y = (bg_h_s - h) // 2
        canvas = bg_s.crop((crop_x, crop_y, crop_x + w, crop_y + h)).convert("RGBA")
        
        # Paste dialogue characters with subtle entrance & floating Y pan
        for c in processed_chars:
            c_img = c["img"]
            # Gentle Floating Y motion
            float_y = int(8 * math.sin(progress * math.pi * 2))
            final_x = c["x"]
            final_y = c["y"] + float_y
            
            canvas.paste(c_img, (final_x, final_y), mask=c_img)
            
        return np.array(canvas.convert("RGB"))

    return VideoClip(get_frame, duration=duration).set_fps(fps)


# =============================================================================
# Main Export Function: merge_and_export
# =============================================================================
def merge_and_export(
    scene_list: list,
    output_name: str,
    font_path: str = "./fonts/Arial.ttf",
    color: str = "random",
    font_size: int = 220,
    target_size: tuple = (1920, 1080),
    bg_music: str = "cool.mp3",
    mode: str = "ultra"
):
    """
    Merges scene clips, audio narration, subtitles, and background music into a final MP4 video.
    Supports Multi-Character Dialogue Scenes & Selective BG Removal.
    """
    print(f"\n🎬 Rendering {len(scene_list)} scenes (Mode: {mode.upper()}, Size: {target_size})...")
    
    temp_scene_files = []
    job_dir = os.path.dirname(output_name) if os.path.dirname(output_name) else "."

    for i, scene in enumerate(scene_list):
        audio_path = scene['audio']
        a_clip = AudioFileClip(audio_path)
        clip_duration = a_clip.duration
        
        if mode == "ultra" and "characters" in scene:
            # Multi-Character Dialogue Ultra Clip
            print(f"🎭 Scene {i+1}: Generating Multi-Character Dialogue Ultra Clip...")
            v_clip = create_multi_character_ultra_clip(scene, clip_duration, size=target_size)
        else:
            video_path = scene['video'][0] if isinstance(scene['video'], list) else scene['video']
            is_image = str(video_path).lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
            
            if is_image and os.path.exists(video_path):
                v_clip = ImageClip(video_path).resize(height=target_size[1])
            elif os.path.exists(video_path):
                v_clip = VideoFileClip(video_path, audio=False).resize(height=target_size[1])
            else:
                v_clip = ColorClip(size=target_size, color=(15, 10, 35))

            if v_clip.w > target_size[0]:
                v_clip = v_clip.crop(x_center=v_clip.w/2, width=target_size[0])
            elif v_clip.w < target_size[0]:
                v_clip = v_clip.resize(width=target_size[0])
                v_clip = v_clip.crop(y_center=v_clip.h/2, height=target_size[1])

        v_clip = v_clip.set_duration(clip_duration)
        v_clip = v_clip.set_audio(a_clip)

        # Dynamic Subtitle rendering with random position & color animation
        clip_text_segment = scene['text']
        txt_clip = create_dynamic_animated_text(
            full_text=clip_text_segment,
            size=target_size,
            duration=clip_duration,
            font_path=font_path,
            font_size=font_size,
            text_position="random",
            text_color="random"
        )
        
        scene_combined = CompositeVideoClip([v_clip, txt_clip.set_position('center')])
        
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
        
        # Cleanup
        scene_combined.close()
        v_clip.close()
        a_clip.close()
        txt_clip.close()
        del scene_combined, v_clip, a_clip, txt_clip
        gc.collect()
        
        temp_scene_files.append(scene_output)

    # Concatenate clips using RAW FFMPEG
    print(f"🔗 Concatenating {len(temp_scene_files)} scenes via ffmpeg...")
    list_path = os.path.join(job_dir, "concat_list.txt")
    with open(list_path, "w") as f:
        for tf in temp_scene_files:
            f.write(f"file '{tf}'\n")
            
    temp_merged = os.path.join(job_dir, "temp_merged_final.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", temp_merged], check=True)

    # Background Music
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
                bg_music_file = possible[0]

    if bg_music_file and os.path.exists(bg_music_file):
        print(f"🎬 Adding background music: {bg_music_file}...")
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
        print("🎬 Exporting final video...")
        if os.path.exists(temp_merged): os.rename(temp_merged, output_name)
    
    if os.path.exists(list_path): os.remove(list_path)
    for f in temp_scene_files: 
        if os.path.exists(f): os.remove(f)
    
    return output_name