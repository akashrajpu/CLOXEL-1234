import os
import random
import numpy as np
import textwrap
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ImageSequenceClip, VideoClip
from PIL import Image, ImageDraw, ImageFont

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

    def make_frame(t):
        i = int(t * fps)
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if not words:
            return np.array(img)
            
        # Current word highlight logic
        word_idx = int((i / total_frames) * len(words))
        if word_idx >= len(words): word_idx = len(words) - 1
        
        # 3. Text ko chunks mein baantna
        is_landscape = size[0] > size[1]
        chunk_size = 12 if is_landscape else 3
        chunk_idx = word_idx // chunk_size
        
        start_idx = chunk_idx * chunk_size
        end_idx = start_idx + chunk_size
        current_chunk_words = words[start_idx:end_idx]
        target_local_idx = word_idx - start_idx
        
        chunk_text = " ".join(current_chunk_words)
        wrap_width = 40 if is_landscape else 12
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
            
        return np.array(img)
    
    return VideoClip(make_frame, duration=duration).set_fps(fps)
    
def merge_and_export(scene_list, output_name, font_path="./fonts/UTM Kabel KT.ttf", color="#FFEE00", font_size=220, target_size=(1080, 1920)):
    """
    Har scene ka apna audio, apna video, aur apni text script merge karta hai.
    """
    print(f"\n🎸 Merging distinct scenes (Size: {target_size})...")
    
    final_combined_scenes = []

    for i, scene in enumerate(scene_list):
        video_path = scene['video'][0] if isinstance(scene['video'], list) else scene['video']
        audio_path = scene['audio']
        
        # Audio clip
        a_clip = AudioFileClip(audio_path)
        clip_duration = a_clip.duration
        
        # Video clip taiyaar karein
        v_clip = VideoFileClip(video_path).resize(height=target_size[1])
        if v_clip.w > target_size[0]:
            v_clip = v_clip.crop(x_center=v_clip.w/2, width=target_size[0])
        v_clip = v_clip.set_duration(clip_duration)
        v_clip = v_clip.set_audio(a_clip)

        # Text clip (segment specific)
        clip_text_segment = scene['text']
        txt_clip = create_animated_text(clip_text_segment, target_size, clip_duration, font_path, color, font_size)
        
        # Video aur Segmented Subtitle merge karein
        scene_combined = CompositeVideoClip([v_clip, txt_clip.set_position('center')])
        final_combined_scenes.append(scene_combined)

    # Saari clips ko jodein
    video_track = concatenate_videoclips(final_combined_scenes, method="compose")
    total_duration = video_track.duration

    # Background Music Logic
    try:
        music_dir = "./songs" if os.path.isdir("./songs") else "./songs copy"
        bg_music_files = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.lower().endswith(('.mp3', '.wav'))]
        if bg_music_files:
            bg_music = AudioFileClip(random.choice(bg_music_files)).volumex(0.12).set_duration(total_duration)
            from moviepy.audio.AudioClip import CompositeAudioClip
            video_track = video_track.set_audio(CompositeAudioClip([video_track.audio, bg_music]))
    except: pass

    # Final Render
    video_track.write_videofile(output_name, codec="libx264", audio_codec="aac", fps=24)
    
    # Cleanup
    video_track.close()
    for scene in final_combined_scenes: scene.close()
    
    return output_name