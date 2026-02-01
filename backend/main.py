from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import shutil
import ffmpeg
from core.downloader import download_youtube_video
from core.processing import extract_highlight, auto_reframe
from core.transcription import generate_dynamic_subtitles

app = FastAPI(title="AI Video Shorts Generator API")

# Directories
TEMP_DIR = "temp"
OUTPUT_DIR = "output"
os.makedirs(TEMP_DIR, exist_ok=True)
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

def update_status(project_id: str, status: str, message: str = ""):
    project_status[project_id] = {"status": status, "message": message}
    print(f"[{project_id}] Status: {status} - {message}")

def process_pipeline(request: ProcessRequest, project_id: str):
    """
    Full processing pipeline: Download -> Cut -> Reframe -> Transcript -> Burn
    Processed sequentially for each segment.
    """
    try:
        update_status(project_id, "processing", "Starting download...")
        print(f"[{project_id}] Starting processing for {request.youtube_url}")
        
        # 1. Download (Once)
        video_path = download_youtube_video(request.youtube_url, TEMP_DIR)
        
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
            
            # 3. Auto Reframe (9:16)
            reframed_path = os.path.join(OUTPUT_DIR, f"{clip_id}_9_16.mp4")
            auto_reframe(cut_path, reframed_path)
            
            update_status(project_id, "processing", f"Processing Clip {clip_num}/{total_clips}: Generating subtitles...")
            
            # 4. Generate Subtitles (ASS - Karaoke)
            ass_path = generate_dynamic_subtitles(reframed_path)
            
            update_status(project_id, "processing", f"Processing Clip {clip_num}/{total_clips}: Burning subtitles...")
            
            # 5. Burn Subtitles (Hardcode)
            final_output_path = os.path.join(OUTPUT_DIR, f"{clip_id}_final.mp4")
            
            # FFmpeg filter to burn subtitles. 
            ass_path_fwd = ass_path.replace("\\", "/")
            
            input_stream = ffmpeg.input(reframed_path)
            video = input_stream.video.filter('ass', ass_path_fwd)
            audio = input_stream.audio
            
            (
                ffmpeg
                .output(video, audio, final_output_path)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            print(f"[{project_id}] Clip {clip_num} finished: {final_output_path}")
            output_files.append(f"{clip_id}_final.mp4")
        
        # Update status with list of Result Files
        project_status[project_id] = {
            "status": "completed", 
            "message": "All clips processed",
            "outputs": output_files
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
    project_id = str(uuid.uuid4())
    background_tasks.add_task(process_pipeline, request, project_id)
    return {"message": "Processing started", "project_id": project_id}

@app.get("/")
def read_root():
    return {"message": "AI Video Shorts Generator API Running"}
