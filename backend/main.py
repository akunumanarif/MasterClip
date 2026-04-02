from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import shutil
import ffmpeg
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from core.downloader import download_youtube_video
from core.transcription import generate_dynamic_subtitles
from core.email_service import email_service
from core.pipeline.audio_extractor import extract_audio
from core.pipeline.transcriber import transcribe
from core.pipeline.diarizer import diarize
from core.pipeline.segment_merger import merge as merge_segments
from core.pipeline.highlight_detector import detect_highlights
from core.pipeline.renderer import render_clip

app = FastAPI(title="AI Video Shorts Generator API")

# Directories
TEMP_DIR = "temp"
CLIPS_DIR = "clips"
OUTPUT_DIR = "output"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app.mount("/clips", StaticFiles(directory=CLIPS_DIR), name="clips")
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# In-memory project state
project_status: dict = {}
# Stores paths and analysis results between Phase 1 and Phase 2
project_data: dict = {}


def update_status(project_id: str, status: str, message: str = "", **extra):
    project_status[project_id] = {"status": status, "message": message, **extra}
    print(f"[{project_id}] Status: {status} - {message}")


# ─────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    youtube_url: str
    resolution: str = "1080p"
    cookies_file: Optional[str] = None
    pyannote_auth_token: Optional[str] = None
    aspect_ratio: str = "9:16"
    color_grading: str = "none"


class GenerateRequest(BaseModel):
    project_id: str
    selected_indices: List[int]  # Which clip candidates to render (0-based)


# ─────────────────────────────────────────────
# Phase 1: Analyze pipeline (background task)
# ─────────────────────────────────────────────

def analyze_pipeline(request: AnalyzeRequest, project_id: str):
    try:
        update_status(project_id, "analyzing", "Downloading video...")

        project_dir = os.path.join(CLIPS_DIR, project_id)
        os.makedirs(project_dir, exist_ok=True)

        # 1. Download video
        video_path = download_youtube_video(
            request.youtube_url,
            TEMP_DIR,
            request.resolution,
            request.cookies_file
        )
        print(f"[{project_id}] Downloaded: {video_path}")

        # 2. Extract audio
        update_status(project_id, "analyzing", "Extracting audio...")
        audio_path = os.path.join(TEMP_DIR, f"{project_id}_audio.wav")
        extract_audio(video_path, audio_path)

        # 3. Transcribe
        update_status(project_id, "analyzing", "Transcribing with Whisper...")
        transcript = transcribe(audio_path)
        print(f"[{project_id}] Transcribed: {len(transcript.get('words', []))} words, lang={transcript.get('language')}")

        # 4. Diarize
        update_status(project_id, "analyzing", "Running speaker diarization...")
        pyannote_token = request.pyannote_auth_token or os.getenv("PYANNOTE_AUTH_TOKEN", "")
        diarization = diarize(audio_path, pyannote_token)
        print(f"[{project_id}] Diarization: {len(diarization)} segments")

        # 5. Merge words with speaker labels
        update_status(project_id, "analyzing", "Merging transcription with speakers...")
        merged_segments = merge_segments(transcript["words"], diarization)
        print(f"[{project_id}] Merged: {len(merged_segments)} speaker segments")

        # 6. Detect highlights
        update_status(project_id, "analyzing", "Scoring and selecting highlight clips...")
        candidates = detect_highlights(merged_segments)
        print(f"[{project_id}] Found {len(candidates)} clip candidates")

        # Store for Phase 2
        project_data[project_id] = {
            "video_path": video_path,
            "audio_path": audio_path,
            "diarization": diarization,
            "candidates": candidates,
            "aspect_ratio": request.aspect_ratio,
            "color_grading": request.color_grading,
            "project_dir": project_dir,
        }

        update_status(
            project_id,
            "ready_for_review",
            f"Found {len(candidates)} clip candidates. Select which to generate.",
            clip_candidates=candidates
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        update_status(project_id, "error", str(e))


# ─────────────────────────────────────────────
# Phase 2: Generate (render) pipeline (background task)
# ─────────────────────────────────────────────

def generate_pipeline(project_id: str, selected_indices: List[int]):
    try:
        data = project_data.get(project_id)
        if not data:
            update_status(project_id, "error", "Project data not found. Please re-analyze.")
            return

        video_path = data["video_path"]
        audio_path = data["audio_path"]
        diarization = data["diarization"]
        candidates = data["candidates"]
        aspect_ratio = data["aspect_ratio"]
        color_grading = data["color_grading"]
        project_dir = data["project_dir"]

        selected = [candidates[i] for i in selected_indices if i < len(candidates)]
        if not selected:
            update_status(project_id, "error", "No valid clips selected.")
            return

        output_files = []
        total = len(selected)

        for idx, clip in enumerate(selected):
            clip_num = idx + 1
            clip_start = clip["start"]
            clip_end = clip["end"]

            update_status(project_id, "generating",
                          f"Rendering clip {clip_num}/{total} ({clip_start:.0f}s–{clip_end:.0f}s)...")

            # Filter diarization to clip range
            clip_diarization = [
                seg for seg in diarization
                if seg["end"] > clip_start and seg["start"] < clip_end
            ]

            # Render reframed video
            reframed_path = os.path.join(TEMP_DIR, f"{project_id}_clip{clip_num}_reframed.mp4")
            render_clip(
                video_path=video_path,
                audio_path=audio_path,
                clip_start=clip_start,
                clip_end=clip_end,
                output_path=reframed_path,
                diarization=clip_diarization,
                aspect_ratio=aspect_ratio,
                color_grading=color_grading,
            )

            update_status(project_id, "generating",
                          f"Burning subtitles for clip {clip_num}/{total}...")

            # Generate subtitles
            ass_path = generate_dynamic_subtitles(reframed_path)

            # Burn subtitles
            final_filename = f"{project_id}_clip{clip_num}_final.mp4"
            final_path = os.path.join(project_dir, final_filename)
            ass_path_fwd = ass_path.replace("\\", "/")

            input_stream = ffmpeg.input(reframed_path)
            video_stream = input_stream.video.filter("ass", ass_path_fwd)
            audio_stream = input_stream.audio

            (
                ffmpeg
                .output(
                    video_stream, audio_stream, final_path,
                    vcodec="libx264",
                    acodec="aac",
                    **{
                        "crf": 18,
                        "preset": "slow",
                        "profile:v": "high",
                        "pix_fmt": "yuv420p",
                        "movflags": "+faststart",
                        "b:a": "192k",
                    }
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            output_files.append({
                "filename": final_filename,
                "url": f"/clips/{project_id}/{final_filename}",
                "start": clip_start,
                "end": clip_end,
                "score": clip.get("score", 0),
                "text_preview": clip.get("text_preview", ""),
            })

            # Clean up temp reframed file
            try:
                os.remove(reframed_path)
            except Exception:
                pass

        # Send email notification
        update_status(project_id, "generating", "Sending email notification...")
        email_sent = email_service.send_clip_notification(project_id, output_files)

        project_status[project_id] = {
            "status": "completed",
            "message": f"Generated {len(output_files)} clips",
            "project_id": project_id,
            "outputs": output_files,
            "email_sent": email_sent,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        update_status(project_id, "error", str(e))


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@app.get("/api/status/{project_id}")
def get_status(project_id: str):
    state = project_status.get(project_id, {"status": "not_found", "message": "Project not found"})
    # Include clip candidates when ready for review
    if state.get("status") == "ready_for_review" and "clip_candidates" not in state:
        data = project_data.get(project_id, {})
        state["clip_candidates"] = data.get("candidates", [])
    return state


@app.post("/api/analyze")
async def analyze_video(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Phase 1: Download + transcribe + diarize + score clips. Returns project_id."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    project_id = f"{timestamp}_{uuid.uuid4().hex[:6]}"
    update_status(project_id, "queued", "Analysis queued...")
    background_tasks.add_task(analyze_pipeline, request, project_id)
    return {"message": "Analysis started", "project_id": project_id}


@app.post("/api/generate")
async def generate_clips(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Phase 2: Render selected clips. project_id must be in ready_for_review state."""
    state = project_status.get(request.project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    if state["status"] not in ("ready_for_review", "completed"):
        raise HTTPException(status_code=400, detail=f"Project is in '{state['status']}' state, not ready for generation")
    if not request.selected_indices:
        raise HTTPException(status_code=400, detail="No clips selected")

    update_status(request.project_id, "generating", "Starting render...")
    background_tasks.add_task(generate_pipeline, request.project_id, request.selected_indices)
    return {"message": "Generation started", "project_id": request.project_id}


# ─────────────────────────────────────────────
# Quote generator (preserved)
# ─────────────────────────────────────────────

from core.image_gen import create_quote_image
from core.video_gen import create_quote_video


class QuoteRequest(BaseModel):
    category: str = "life"
    language: str = "en"
    format: str = "image"


@app.post("/api/generate-quote")
def generate_quote(request: QuoteRequest):
    ext = "mp4" if request.format == "video" else "png"
    filename = f"quote_{uuid.uuid4()}.{ext}"
    output_path = os.path.join(OUTPUT_DIR, filename)
    try:
        if request.format == "video":
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
