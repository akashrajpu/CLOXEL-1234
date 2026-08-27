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
    font_path: str = "./fonts/Arial.ttf",
    font_size: int = 220,
    text_color: str = "random",
    text_position: str = "random",
    fps: int = 20,
    is_ultra_mode: bool = False
) -> VideoClip:
    """
    Generates dynamic multi-color subtitles. Ultra Mode enables keyword sizing & side alignment.
    """
    total_frames = int(duration * fps)
    if total_frames <= 0: total_frames = 1
    
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
            y_text = size[1] - total_h - int(size[1] * 0.14)
        else: # center
            y_text = (size[1] - total_h) / 2
        
        # Multi-color & side alignment ONLY for Ultra Mode!
        if is_ultra_mode:
            rand_pos_mode = random.choice(["side_left", "side_right", "center"])
            if rand_pos_mode == "side_left":
                x_align_offset = int(size[0] * 0.08)
            elif rand_pos_mode == "side_right":
                x_align_offset = int(size[0] * 0.45)
            else:
                x_align_offset = None
        else:
            x_align_offset = None

        local_word_count = 0
        shadow_offset = max(3, int(active_font.size * 0.05))
        color_palette = ["#FFD700", "#00FFFF", "#34D399", "#FF5722", "#E0E7FF"]
        
        for line_words in lines:
            space_bbox = draw.textbbox((0, 0), " ", font=active_font)
            space_w = space_bbox[2] - space_bbox[0]
            
            line_total_w = sum((draw.textbbox((0, 0), w, font=active_font)[2] - draw.textbbox((0, 0), w, font=active_font)[0]) for w in line_words) + space_w * (len(line_words) - 1)
            
            if x_align_offset is not None:
                current_x = x_align_offset
            else:
                current_x = (size[0] - line_total_w) / 2
            
            for w in line_words:
                if is_ultra_mode:
                    is_bold_keyword = (len(w) > 4 or w[0].isupper())
                    w_font = load_font(int(user_font_size * 1.15)) if is_bold_keyword else active_font
                    if local_word_count == target_local_idx:
                        color = highlight_color
                    elif is_bold_keyword:
                        color = color_palette[local_word_count % len(color_palette)]
                    else:
                        color = "#FFFFFF"
                else:
                    w_font = active_font
                    color = highlight_color if local_word_count <= target_local_idx else "white"
                
                # Drop shadow & bold text outline
                draw.text((current_x + shadow_offset, y_text + shadow_offset), w, font=w_font, fill=(0, 0, 0, 240))
                draw.text((current_x, y_text), w, font=w_font, fill=color)
                
                w_bbox = draw.textbbox((0, 0), w, font=w_font)
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


def generate_ink_brush_mask(size: tuple) -> Image.Image:
    """Generates a procedural high-resolution Ink Brush / Paint Reveal Mask PNG with rough organic edges."""
    w, h = size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    
    # Inner rectangular core
    margin_w = int(w * 0.04)
    margin_h = int(h * 0.04)
    draw.rectangle([margin_w, margin_h, w - margin_w, h - margin_h], fill=255)
    
    # Generate jagged rough brush strokes along borders
    random.seed(42)
    for x in range(margin_w, w - margin_w, 8):
        jitter_top = random.randint(-18, 25)
        jitter_bot = random.randint(-18, 25)
        draw.line([(x, margin_h + jitter_top), (x, margin_h)], fill=255, width=6)
        draw.line([(x, h - margin_h), (x, h - margin_h + jitter_bot)], fill=255, width=6)
        
    for y in range(margin_h, h - margin_h, 8):
        jitter_left = random.randint(-18, 25)
        jitter_right = random.randint(-18, 25)
        draw.line([(margin_w + jitter_left, y), (margin_w, y)], fill=255, width=6)
        draw.line([(w - margin_w, y), (w - margin_w + jitter_right, y)], fill=255, width=6)
        
    return mask.filter(ImageFilter.GaussianBlur(radius=6))

def apply_color_filter(pil_img: Image.Image, filter_style: str = "warm_epic") -> Image.Image:
    """Applies cinematic color grading LUTs, Film Grain, Dust, Haze Smoke & Vintage Paper Textures."""
    img = pil_img.copy().convert("RGB")
    w, h = img.size

    if filter_style == "warm_epic":
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.30)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.20)
        overlay = Image.new("RGB", img.size, (255, 185, 110))
        img = Image.blend(img, overlay, alpha=0.15)
    elif filter_style == "vintage_parchment":
        gray = img.convert("L")
        sepia = ImageOps.colorize(gray, "#261508", "#ffe6cc")
        img = Image.blend(img, sepia, alpha=0.80)
    elif filter_style == "dramatic_cinematic":
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.35)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.15)

    # 1. Old Paper Scratches & Vintage Parchment Texture Overlay
    paper_tex = create_parchment_background((w, h), color_theme="warm")
    img = Image.blend(img, paper_tex, alpha=0.18)

    # 2. Orange Light Leak & Dust Particles Overlay
    light_leak = Image.new("RGB", (w, h), (255, 130, 40))
    glow_mask = Image.new("L", (w, h), 0)
    g_draw = ImageDraw.Draw(glow_mask)
    g_draw.ellipse([-int(w*0.2), -int(h*0.2), int(w*0.6), int(h*0.6)], fill=180)
    glow_mask = glow_mask.filter(ImageFilter.GaussianBlur(radius=80))
    img = Image.composite(light_leak, img, glow_mask)

    return img

def create_parchment_background(size: tuple, color_theme: str = "warm") -> Image.Image:
    """Generates a 4K vintage parchment/canvas texture background with paper scratches and vignette."""
    w, h = size
    bg = Image.new("RGB", (w, h), (235, 215, 185) if color_theme == "warm" else (220, 200, 170))
    vignette = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(vignette)
    cx, cy = w / 2, h / 2
    max_r = math.sqrt(cx**2 + cy**2)
    for r in range(int(max_r), 0, -10):
        alpha = int(255 * (r / max_r)**1.8)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=min(255, alpha + 60))
    vignette_blur = vignette.filter(ImageFilter.GaussianBlur(radius=30))
    dark_overlay = Image.new("RGB", (w, h), (40, 25, 15))
    bg = Image.composite(bg, dark_overlay, vignette_blur)
    return bg

def create_ultra_photo_motion_clip(
    photo_path: str,
    fg_photo_path: str = None,
    duration: float = 5.0,
    size: tuple = (1920, 1080),
    filter_style: str = "warm_epic",
    cutout_pos: str = "left",
    motion_type: str = "zoom_in",
    fps: int = 20
) -> VideoClip:
    """Creates an Ultra Photo Motion Video Clip with Ink Brush Mask Edges, Smoke Haze, Particles, & Dynamic Zoom/Pan."""
    w, h = size
    print(f"🎨 [Ultra Engine] Generating 3D Ultra Clip (BG: {photo_path}, FG: {fg_photo_path}, Filter: {filter_style}, Motion: {motion_type.upper()})...")
    
    if not photo_path or not os.path.exists(photo_path):
        bg_pil = create_parchment_background(size, color_theme="warm")
        def get_fallback_frame(t):
            return np.array(bg_pil.convert("RGB"))
        return VideoClip(get_fallback_frame, duration=duration).set_fps(fps)

    # 1. Background Photo (Layer 1 - 0% BG Removal)
    is_video_file = str(photo_path).lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))
    orig_pil = None
    if is_video_file and os.path.exists(photo_path):
        try:
            v_temp = VideoFileClip(photo_path)
            frame_t = min(1.0, v_temp.duration / 2.0)
            raw_frame = v_temp.get_frame(frame_t)
            orig_pil = Image.fromarray(raw_frame).convert("RGBA")
            v_temp.close()
        except Exception:
            orig_pil = None
    else:
        try:
            orig_pil = Image.open(photo_path).convert("RGBA")
        except Exception:
            orig_pil = None

    if orig_pil is None:
        bg_pil = create_parchment_background(size, color_theme="warm")
        def get_fallback_frame(t):
            return np.array(bg_pil.convert("RGB"))
        return VideoClip(get_fallback_frame, duration=duration).set_fps(fps)

    bg_pil = apply_color_filter(orig_pil.convert("RGB"), filter_style=filter_style)
    aspect_bg = bg_pil.width / bg_pil.height
    canvas_aspect = w / h
    if aspect_bg > canvas_aspect:
        bg_h_fit = h
        bg_w_fit = int(h * aspect_bg)
    else:
        bg_w_fit = w
        bg_h_fit = int(w / aspect_bg)
    bg_pil = bg_pil.resize((bg_w_fit, bg_h_fit), Image.LANCZOS)

    # 2. Foreground Character Cutout Photo with Ink Brush Mask PNG Edges
    has_cutout = False
    fg_resized = None
    cutout_src_path = fg_photo_path if (fg_photo_path and os.path.exists(fg_photo_path)) else photo_path
    
    if remove_background and cutout_src_path:
        try:
            char_orig = Image.open(cutout_src_path).convert("RGBA")
            fg_pil = remove_background(char_orig)
            if fg_pil.mode == "RGBA" and fg_pil.getextrema()[3][0] < 255:
                fg_filtered = apply_color_filter(fg_pil.convert("RGB"), filter_style=filter_style)
                fg_filtered.putalpha(fg_pil.split()[3])
                target_fg_h = int(h * 0.85)
                aspect_fg = fg_filtered.width / fg_filtered.height
                target_fg_w = int(target_fg_h * aspect_fg)
                fg_resized = fg_filtered.resize((target_fg_w, target_fg_h), Image.LANCZOS)
                
                # Apply Ink Brush Matte / Mask to Character Cutout Edges
                ink_mask = generate_ink_brush_mask((fg_resized.width, fg_resized.height))
                cur_alpha = fg_resized.split()[3]
                combined_alpha = Image.composite(cur_alpha, Image.new("L", cur_alpha.size, 0), ink_mask)
                fg_resized.putalpha(combined_alpha)
                has_cutout = True
        except Exception as e_cut:
            print(f"⚠️ Character cutout extraction skip: {e_cut}")
            has_cutout = False

    def get_frame(t):
        progress = t / duration if duration > 0 else 0
        
        # Dynamic Camera Motions per Scene: Zoom In / Zoom Out / Pan Right / Pan Left
        if motion_type == "zoom_in":
            bg_scale = 1.0 + (0.18 * progress)
            pan_x_factor = 0.5
            pan_y_factor = 0.5
        elif motion_type == "zoom_out":
            bg_scale = 1.20 - (0.15 * progress)
            pan_x_factor = 0.5
            pan_y_factor = 0.5
        elif motion_type == "pan_right":
            bg_scale = 1.15
            pan_x_factor = 0.30 + (0.40 * progress)
            pan_y_factor = 0.5
        else: # pan_left
            bg_scale = 1.15
            pan_x_factor = 0.70 - (0.40 * progress)
            pan_y_factor = 0.5
            
        bg_w_scaled = int(bg_w_fit * bg_scale)
        bg_h_scaled = int(bg_h_fit * bg_scale)
        bg_scaled = bg_pil.resize((bg_w_scaled, bg_h_scaled), Image.BILINEAR)
        
        crop_x = int((bg_w_scaled - w) * pan_x_factor)
        crop_y = int((bg_h_scaled - h) * pan_y_factor)
        crop_x = max(0, min(bg_w_scaled - w, crop_x))
        crop_y = max(0, min(bg_h_scaled - h, crop_y))
        
        frame_canvas = bg_scaled.crop((crop_x, crop_y, crop_x + w, crop_y + h)).convert("RGBA")
        
        # Animated Lighting Pulse & Film Haze
        light_pulse = 1.0 + (0.09 * math.sin(progress * math.pi * 2))
        frame_canvas = ImageEnhance.Brightness(frame_canvas.convert("RGB")).enhance(light_pulse).convert("RGBA")
        
        # Character Cutout strictly grounded to bottom border (Never floats up, 100% Bottom Grounded)
        if has_cutout and fg_resized:
            fg_scale = 1.0 + (0.03 * math.sin(progress * math.pi))
            cur_fg_w = int(fg_resized.width * fg_scale)
            cur_fg_h = int(fg_resized.height * fg_scale)
            fg_cur = fg_resized.resize((cur_fg_w, cur_fg_h), Image.BILINEAR)
            
            if cutout_pos == "right":
                fg_x = w - cur_fg_w
            else: # left
                fg_x = 0
                
            fg_y = h - cur_fg_h # 100% Flush Bottom Alignment
            frame_canvas.paste(fg_cur, (fg_x, fg_y), mask=fg_cur)
            
        return np.array(frame_canvas.convert("RGB"))

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
        
        if mode == "ultra":
            if "characters" in scene:
                print(f"🎭 Scene {i+1}: Generating Multi-Character Dialogue Ultra Clip...")
                v_clip = create_multi_character_ultra_clip(scene, clip_duration, size=target_size)
            else:
                video_paths = scene['video'] if isinstance(scene['video'], list) else [scene['video']]
                bg_path = video_paths[0]
                fg_path = video_paths[1] if len(video_paths) > 1 else None
                filters = ["warm_epic", "vintage_parchment", "dramatic_cinematic"]
                filter_choice = filters[i % len(filters)]
                side_pos = "left" if i % 2 == 0 else "right"
                motions = ["zoom_in", "zoom_out", "pan_right", "pan_left"]
                motion_choice = motions[i % len(motions)]
                print(f"✨ Scene {i+1}: Generating Ultra Dual-Photo Motion Clip (Filter: {filter_choice}, Motion: {motion_choice.upper()}, Side: {side_pos.upper()})...")
                v_clip = create_ultra_photo_motion_clip(bg_path, fg_photo_path=fg_path, duration=clip_duration, size=target_size, filter_style=filter_choice, cutout_pos=side_pos, motion_type=motion_choice)
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
            text_color="random",
            is_ultra_mode=(mode == "ultra")
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