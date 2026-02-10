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
    # ASS Header
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,70,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,2,50,50,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # PrimaryColour (Text) is White (&H00FFFFFF)
    # OutlineColour default is White (&H00FFFFFF) - invisible
    # Border default is 0 (no border)
    # Each word turns red border ON at start, OFF at end
    
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        
        for segment in result["segments"]:
            words = segment["words"]
            
            # Use larger chunks (6 words) split into 2 lines for "Center Stacked" look
            chunk_size = 6
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i+chunk_size]
                if not chunk: continue
                
                start_time = format_timestamp(chunk[0]["start"])
                end_time = format_timestamp(chunk[-1]["end"])
                chunk_start_seconds = chunk[0]["start"]
                
                text_content = ""
                split_idx = (len(chunk) + 1) // 2 # Split roughly in half (e.g. 3 on top, 3 on bottom)
                
                for idx, word in enumerate(chunk):
                    # Insert Line Break at split point
                    if idx == split_idx:
                        text_content += "\\N"
                    
                    # Karaoke duration in centiseconds
                    duration = int((word["end"] - word["start"]) * 100) 
                    text = word["word"].strip().upper() # ALL CAPS
                    
                    # Calculate absolute timing for this word within chunk (milliseconds)
                    word_start_ms = int((word["start"] - chunk_start_seconds) * 1000)
                    word_end_ms = int((word["end"] - chunk_start_seconds) * 1000)
                    
                    # KARAOKE STYLE: 
                    # - Default: white text, no background
                    # - Speaking: white text WITH red background
                    # Using \t(t1,t2,effect) for timed transformation
                    # \3c = outline/border color, \bord = border thickness
                    
                    # Each word starts with no border (inherited from style)
                    # At word_start_ms: turn ON red border (instant)
                    # At word_end_ms: turn OFF border (instant)
                    
                    turn_on = f"\\t({word_start_ms},{word_start_ms},\\bord10\\3c&H0000FF&)"
                    turn_off = f"\\t({word_end_ms},{word_end_ms},\\bord0\\3c&HFFFFFF&)"
                    
                    # Initial state: no border (\bord0)
                    text_content += f"{{\\bord0\\3c&HFFFFFF&{turn_on}{turn_off}\\be3\\k{duration}}}{text} "
                
                
                f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text_content.strip()}\n")

    return ass_path
