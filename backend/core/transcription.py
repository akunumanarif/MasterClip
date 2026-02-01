import whisper
import os
import datetime

def format_timestamp(seconds: float):
    """Converts seconds to HH:MM:SS.mm format for ASS."""
    td = datetime.timedelta(seconds=seconds)
    # timedelta string is like 0:00:00.000000
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int(td.microseconds / 10000) # ASS uses centiseconds (2 digits)
    return f"{hours}:{minutes:02d}:{secs:02d}.{millis:02d}"

def generate_dynamic_subtitles(video_path: str, model_size: str = "small"):
    """
    Transcribes video using Whisper and generates an ASS file with word-level highlighting (Karaoke).
    Returns the path to the ASS file.
    """
    # Force CPU to use FP32 if needed, or suppress warning.
    # Changing model to 'small' for better accuracy than 'base'.
    model = whisper.load_model(model_size)
    result = model.transcribe(video_path, word_timestamps=True)
    
    ass_path = os.path.splitext(video_path)[0] + ".ass"
    
    # ASS Header
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # PrimaryColour is White (FFFFFF), SecondaryColour is Yellow (00FFFF) -- BGR format in ASS
    
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        
        for segment in result["segments"]:
            words = segment["words"]
            # We want to display a group of words (phrase) at a time, e.g., 3-5 words
            # For simplicity in this iteration, let's display the whole segment (if short) 
            # or break it into chunks of ~4 words.
            
            chunk_size = 5
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i+chunk_size]
                if not chunk: continue
                
                start_time = format_timestamp(chunk[0]["start"])
                end_time = format_timestamp(chunk[-1]["end"])
                
                # Build the karaoke text: {\k15}Word {\k20}Word
                text_content = ""
                for word in chunk:
                    # Duration in centiseconds
                    duration = int((word["end"] - word["start"]) * 100) 
                    text = word["word"].strip()
                    # Highlight color approach: 
                    # Use {\1c&H00FFFF&} for highlight, {\1c&HFFFFFF&} for normal?
                    # Karaoke tag {\k<duration>} highlights the text progressively.
                    # Or for "active word" style:
                    # We can't easily do "Karaoke" fill without a specific font/player support sometimes.
                    # A better "OpusClip" style is: All words white, Current word Yellow.
                    # But standard ASS karaoke {\k} just fills the color from Secondary to Primary.
                    # Let's try standard Karaoke first: Output is Secondary (Yellow) -> Primary (White).
                    # Wait, usually it's Primary -> Secondary.
                    # Let's stick to explicit coloring if we want "Active Word" vs "Past Word".
                    # Actually, {\k} is the easiest "moving" effect.
                    
                    text_content += f"{{\\k{duration}}}{text} "
                
                f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text_content.strip()}\n")

    return ass_path
