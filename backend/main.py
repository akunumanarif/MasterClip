from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import shutil
import ffmpeg
from datetime import datetime
from core.downloader import download_youtube_video
from core.processing import extract_highlight, auto_reframe
from core.transcription import generate_dynamic_subtitles
from core.email_service import email_service

app = FastAPI(title="AI Video Shorts Generator API")

# Directories
TEMP_DIR = "temp"
CLIPS_DIR = "clips"  # Changed from output to clips for persistent storage
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)

# Mount clips directory for serving persistent files
app.mount("/clips", StaticFiles(directory=CLIPS_DIR), name="clips")

# Keep backward compatibility for quote generator (uses output dir temporarily)
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# In-memory storage for project status (in a real app, use a database)
project_status = {}

from typing import List

class ClipSegment(BaseModel):
    start_time: str
    end_time: str

class ProcessRequest(BaseModel):
    youtube_url: str
    segments: List[ClipSegment]
    project_name: str = "Untitled"
    resolution: str = "1080p" # Default to High Quality
    cookies_file: Optional[str] = None # Optional: Path to YouTube cookies file
    color_grading: str = "none" # Color grading preset

def update_status(project_id: str, status: str, message: str = ""):
    project_status[project_id] = {"status": status, "message": message}
    print(f"[{project_id}] Status: {status} - {message}")

def process_pipeline(request: ProcessRequest, project_id: str):
    """
    Full processing pipeline: Download -> Cut -> Reframe -> Transcript -> Burn
    Processed sequentially for each segment.
    Stores clips in persistent directory and sends email notification.
    """
    try:
        update_status(project_id, "processing", "Starting download...")
        print(f"[{project_id}] Starting processing for {request.youtube_url} @ {request.resolution}")
        
        # Create project-specific directory for persistent storage
        project_dir = os.path.join(CLIPS_DIR, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        # 1. Download (Once)
        video_path = download_youtube_video(
            request.youtube_url, 
            TEMP_DIR, 
            request.resolution,
            request.cookies_file
        )
        
        output_files = []
        total_clips = len(request.segments)
        
        for i, segment in enumerate(request.segments):
            clip_num = i + 1
            clip_id = f"{project_id}_clip{clip_num}"
            
            update_status(project_id, "processing", f"Processing Clip {clip_num}/{total_clips}: Cutting...")
            
            # 2. Extract Highlight
            cut_path = os.path.join(TEMP_DIR, f"{clip_id}_cut.mp4")
            extract_highlight(video_path, segment.start_time, segment.end_time, cut_path)
            
            update_status(project_id, "processing", f"Processing Clip {clip_num}/{total_clips}: Reframing (Face Detection)...")
            
            # 3. Auto Reframe (9:16) with Color Grading - temporary location
            reframed_temp_path = os.path.join(TEMP_DIR, f"{clip_id}_9_16.mp4")
            auto_reframe(cut_path, reframed_temp_path, color_grading=request.color_grading)
            
            update_status(project_id, "processing", f"Processing Clip {clip_num}/{total_clips}: Generating subtitles...")
            
            # 4. Generate Subtitles (ASS - Karaoke)
            ass_path = generate_dynamic_subtitles(reframed_temp_path)
            
            update_status(project_id, "processing", f"Processing Clip {clip_num}/{total_clips}: Burning subtitles...")
            
            # 5. Burn Subtitles (Hardcode) - save to persistent project directory
            final_filename = f"{clip_id}_final.mp4"
            final_output_path = os.path.join(project_dir, final_filename)
            
            # FFmpeg filter to burn subtitles with HIGH QUALITY settings
            ass_path_fwd = ass_path.replace("\\", "/")
            
            input_stream = ffmpeg.input(reframed_temp_path)
            video = input_stream.video.filter('ass', ass_path_fwd)
            audio = input_stream.audio
            
            # Use same high-quality settings as reframing for consistency
            # NOTE: When using CRF, do NOT specify video_bitrate (let CRF control it)
            (
                ffmpeg
                .output(
                    video, audio, final_output_path,
                    vcodec='libx264',
                    acodec='aac',
                    **{
                        'crf': 18,                     # High quality (18 = visually lossless)
                        'preset': 'slow',              # Better compression
                        'profile:v': 'high',           # H.264 High Profile
                        'pix_fmt': 'yuv420p',          # Compatibility
                        'movflags': '+faststart',      # Web optimization
                        'b:a': '192k'                  # High quality audio (use b:a not audio_bitrate)
                    }
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            print(f"[{project_id}] Clip {clip_num} finished: {final_output_path}")
            
            # Store clip info with filename and URL
            output_files.append({
                "filename": final_filename,
                "url": f"/clips/{project_id}/{final_filename}"
            })
        
        # Send email notification with download links
        update_status(project_id, "processing", "Sending email notification...")
        email_sent = email_service.send_clip_notification(project_id, output_files)
        
        # Update status with list of Result Files
        project_status[project_id] = {
            "status": "completed", 
            "message": "All clips processed",
            "project_id": project_id,
            "outputs": output_files,
            "email_sent": email_sent
        }
        
    except Exception as e:
        print(f"[{project_id}] Error: {str(e)}")
        update_status(project_id, "error", str(e))
        # In a real app, update DB status to 'error'

@app.get("/api/status/{project_id}")
def get_status(project_id: str):
    return project_status.get(project_id, {"status": "not_found", "message": "Project not found"})

@app.post("/api/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks):
    # Generate unique project ID with timestamp + random component
    # Format: YYYYMMDDHHMMSS_XXXXXX (e.g., 20260217192230_a8f3b2)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:6]
    project_id = f"{timestamp}_{random_suffix}"
    
    background_tasks.add_task(process_pipeline, request, project_id)
    return {"message": "Processing started", "project_id": project_id}

from core.image_gen import create_quote_image

from core.video_gen import create_quote_video

class QuoteRequest(BaseModel):
    category: str = "life"
    language: str = "en"
    format: str = "image" # image | video

@app.post("/api/generate-quote")
def generate_quote(request: QuoteRequest):
    """Generates a motivational quote image or video and returns the file URL."""
    ext = "mp4" if request.format == "video" else "png"
    filename = f"quote_{uuid.uuid4()}.{ext}"
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    try:
        if request.format == "video":
             # Video generation (can be slow, might need background task in real app, but ok for now)
             create_quote_video(output_path, category=request.category, language=request.language)
        else:
             create_quote_image(output_path, category=request.category, language=request.language)
             
        return {"url": f"/output/{filename}", "type": request.format}
    except Exception as e:
        print(f"Error generating quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "AI Video Shorts Generator API Running"}
