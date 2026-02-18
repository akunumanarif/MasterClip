
import os
import random
import requests
import ffmpeg
import textwrap
from .image_gen import fetch_quote, translate_text

# Hardcoded fallback videos (Pixabay - Royalty Free Direct Links)
# Note: Pixabay links can expire or change, but typically last longer than direct Pexels scraping.
# Ideally we host these ourselves or use a stable CDN. 
# Using a few known stable-ish URLs or re-trying requests.
# Hardcoded fallback videos (Mixkit / Sample Videos - Public Domain)
# Hardcoded fallback videos (Test Videos)
FALLBACK_VIDEOS = [
    "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
]

def fetch_video_background(category="life"):
    """Fetches a video URL from Fallback list."""
    return random.choice(FALLBACK_VIDEOS)

def download_video(url, output_path):
    """Downloads video from URL using requests."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        # Use requests for direct file links
        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading video: {e}")
        return False

def create_quote_video(output_path, category="life", language="en"):
    """Generates a vertical quote video."""
    
    # 1. Get Content
    quote, author = fetch_quote(category)
    if language == "id":
        quote = translate_text(quote, "id")
    
    # 2. Get Video
    video_url = fetch_video_background(category)
    temp_video = "temp_bg_video.mp4"
    
    use_synthetic = False
    if not download_video(video_url, temp_video):
        print("Download failed. Using synthetic video background.")
        use_synthetic = True
    
    try:
        # 3. FFmpeg Processing
        duration = 15
        
        # Escape text for FFmpeg drawtext
        def escape_text(text):
            return text.replace("\\", "\\\\").replace("'", "'\\''").replace(":", "\\:")
        
        quote_esc = escape_text(quote)
        author_esc = escape_text(f"- {author}")
        
        wrapper = textwrap.TextWrapper(width=20) 
        quote_wrapped = wrapper.fill(quote)
        quote_esc_wrapped = escape_text(quote_wrapped)
        
        # Input Stream
        if use_synthetic:
            # Generate dynamic background using simple color or testsrc if download fails
            # Using 'mandelbrot' for a cool dynamic pattern or just 'color'
            # let's use a moving gradient effect if possible, or just a static nice color
            # 'testsrc' is too ugly. 'color' is boring.
            # Let's use 'smptebars' inside a loop? No.
            # Simple dark blue background:
            input_stream = ffmpeg.input('color=c=black:s=1080x1920', f='lavfi', t=duration)
        else:
            input_stream = ffmpeg.input(temp_video, stream_loop=-1)
        
        # Construct filter chain
        if use_synthetic:
             # Just drawing text on black/color background
             v = input_stream
        else:
             # Process downloaded video
             v = (
                input_stream
                .trim(duration=duration)
                .filter('scale', 1080, 1920, force_original_aspect_ratio="increase")
                .crop(1080, 1920)
                .drawbox(0, 0, 'iw', 'ih', color='black@0.4', t='fill')
             )

        # Apply Text Overlay (Common for both)
        v = (
            v.drawtext(
                text=quote_esc_wrapped,
                font=font_arg,
                fontsize=70,
                fontcolor='white',
                x='(w-text_w)/2',
                y='(h-text_h)/2',
                line_spacing=20,
                shadowcolor='black',
                shadowx=2,
                shadowy=2
            )
            .drawtext(
                text=author_esc,
                font=font_arg,
                fontsize=40,
                fontcolor='lightgray',
                x='(w-text_w)/2',
                y='(h/2)+text_h+150',
                shadowcolor='black',
                shadowx=1,
                shadowy=1
            )
        )
        
        output = ffmpeg.output(v, output_path, vcodec='libx264', pix_fmt='yuv420p', t=duration)
        output.run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise e
    finally:
        if os.path.exists(temp_video):
            os.remove(temp_video)

    return output_path
