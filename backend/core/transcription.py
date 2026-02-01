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
Style: Default,Arial,60,&H00FFFF00,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,50,50,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # PrimaryColour (Filled) is Cyan (&H00FFFF00 - BGR: 00 FFFF)
    # SecondaryColour (Unfilled) is White (&H00FFFFFF)
    
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
                        # Remove trailing space from previous word if any, though ASS ignores it usually.
                        # We just insert \N. 
                        # Note: The previous word added a space. \N will make it a newline. 
                        text_content += "\\N"
                    
                    # Duration in centiseconds for karaoke
                    duration = int((word["end"] - word["start"]) * 100) 
                    text = word["word"].strip().upper() # ALL CAPS
                    
                    # Animation Logic: "Snap-Pop" (Kick Drum Style)
                    # Instead of growing slowly (which causes jitter), we SNAP to big, then shrink.
                    # This feels punchier and reduces the time the text is 'moving' outward.
                    
                    rel_start = int((word["start"] - chunk_start_seconds) * 1000)
                    rel_end = int((word["end"] - chunk_start_seconds) * 1000)
                    
                    # Pop Peak: slightly reduced to 110% to minimize layout shift artifacts
                    # Border: Pop from 3 to 6 for extra emphasis without layout shift
                    
                    # 1. Instant Pop Up (at start time)
                    # We use a very short transition (50ms) effectively instant
                    pop_dur = 50
                    t_pop_end = rel_start + pop_dur
                    if t_pop_end > rel_end: t_pop_end = rel_end
                    
                    # 2. Shrink Down (rest of duration)
                    
                    # Tag: \t(start, end, accel, attrs)
                    # \t(t1, t2, \fscx110\fscy110\bord6) -> Snap Up
                    # \t(t2, t3, \fscx100\fscy100\bord3) -> Shrink Down
                    
                    anim_tags = f"\\t({rel_start},{t_pop_end},\\fscx110\\fscy110\\bord6)\\t({t_pop_end},{rel_end},\\fscx100\\fscy100\\bord3)"
                    
                    text_content += f"{{\\k{duration}}}{{{anim_tags}}}{text} "
                
                f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text_content.strip()}\n")

    return ass_path
