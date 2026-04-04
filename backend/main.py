from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import asyncio
import shutil
import subprocess
import ffmpeg
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
from core.sheets_service import SheetsService
from core.drive_service import DriveService

# ─────────────────────────────────────────────
# Google Sheets + Scheduler setup
# ─────────────────────────────────────────────

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1LjiJ-LAOXX3MKiarUSAmRS7BKeUlsglSiiBDXU24C-I")
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_sheets_credentials.json")
CRON_INTERVAL_MINUTES = int(os.getenv("CRON_INTERVAL_MINUTES", "15"))

DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
DRIVE_TOKEN_PATH = os.getenv("GOOGLE_DRIVE_TOKEN_PATH", "credentials/google_drive_token.json")

_sheets_service: Optional[SheetsService] = None
_cron_running = False
scheduler = AsyncIOScheduler()


def get_sheets_service() -> Optional[SheetsService]:
    global _sheets_service
    if _sheets_service is None and os.path.exists(CREDENTIALS_PATH):
        _sheets_service = SheetsService(CREDENTIALS_PATH, SPREADSHEET_ID)
    return _sheets_service


def get_drive_service() -> Optional[DriveService]:
    if DRIVE_FOLDER_ID and os.path.exists(DRIVE_TOKEN_PATH):
        return DriveService(DRIVE_TOKEN_PATH, DRIVE_FOLDER_ID)
    return None


async def run_auto_process():
    """Cron 1: Find unprocessed videos in sheet, run full pipeline, send email, update sheet."""
    global _cron_running
    if _cron_running:
        print("[AutoProcess] Skipping: previous run still in progress")
        return

    svc = get_sheets_service()
    if not svc:
        print("[AutoProcess] Sheets credentials not found, skipping")
        return

    _cron_running = True
    try:
        unprocessed = svc.get_unprocessed_videos()
        if not unprocessed:
            print("[AutoProcess] No unprocessed videos found")
            return

        print(f"[AutoProcess] Found {len(unprocessed)} video(s) to process")
        loop = asyncio.get_event_loop()

        for video in unprocessed:
            url = video["url"]
            row_index = video["row_index"]
            print(f"[AutoProcess] Processing row {row_index}: {url}")

            # Flag as processing immediately to prevent duplicate runs
            svc.mark_processing(row_index)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            project_id = f"auto_{timestamp}_{uuid.uuid4().hex[:6]}"

            try:
                # Phase 1 — analyze
                request = AnalyzeRequest(
                    youtube_url=url,
                    resolution="1080p",
                    aspect_ratio="9:16",
                    color_grading="none",
                )
                await loop.run_in_executor(None, analyze_pipeline, request, project_id)

                state = project_status.get(project_id, {})
                if state.get("status") != "ready_for_review":
                    print(f"[AutoProcess] Phase 1 failed: {state.get('message', 'unknown')}")
                    svc.unmark_processing(row_index)
                    continue

                svc.mark_downloaded(row_index)

                # Phase 2 — render all clips
                candidates = project_data.get(project_id, {}).get("candidates", [])
                if not candidates:
                    print(f"[AutoProcess] No clip candidates found for {url}")
                    svc.mark_processed(row_index)
                    svc.unmark_processing(row_index)
                    continue

                all_indices = list(range(len(candidates)))
                await loop.run_in_executor(None, generate_pipeline, project_id, all_indices)

                state = project_status.get(project_id, {})
                if state.get("status") == "completed":
                    svc.mark_processed(row_index)
                    svc.unmark_processing(row_index)
                    print(f"[AutoProcess] Done: {url} → {len(candidates)} clip(s)")
                else:
                    print(f"[AutoProcess] Phase 2 failed: {state.get('message', 'unknown')}")
                    svc.unmark_processing(row_index)

            except Exception as video_err:
                print(f"[AutoProcess] Error processing row {row_index}: {video_err}")
                svc.unmark_processing(row_index)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[AutoProcess] Error: {e}")
    finally:
        _cron_running = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_auto_process, "interval", minutes=CRON_INTERVAL_MINUTES, id="auto_process")
    scheduler.start()
    print(f"[Scheduler] Cron 1 started — auto-process every {CRON_INTERVAL_MINUTES} min")
    yield
    scheduler.shutdown()


app = FastAPI(title="AI Video Shorts Generator API", lifespan=lifespan)

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
        video_path, video_title = download_youtube_video(
            request.youtube_url,
            TEMP_DIR,
            request.resolution,
            request.cookies_file
        )
        print(f"[{project_id}] Downloaded: {video_path} | Title: {video_title}")

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
            "video_title": video_title,
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

            # Burn subtitles using subprocess for proper error reporting
            final_filename = f"{project_id}_clip{clip_num}_final.mp4"
            final_path = os.path.join(project_dir, final_filename)

            # Escape colons in path for ffmpeg filter (needed on all platforms)
            # ffmpeg ass filter uses filter-graph syntax where : is a separator
            ass_path_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

            subtitle_cmd = [
                "ffmpeg", "-y",
                "-i", reframed_path,
                "-vf", f"ass={ass_path_escaped}",
                "-c:v", "libx264",
                "-crf", "18",
                "-preset", "slow",
                "-profile:v", "high",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-c:a", "aac",
                "-b:a", "192k",
                final_path
            ]
            print(f"    Burning subtitles: {' '.join(subtitle_cmd)}")
            sub_result = subprocess.run(subtitle_cmd, capture_output=True, text=True)
            if sub_result.returncode != 0:
                print(f"    FFmpeg subtitle stderr:\n{sub_result.stderr[-3000:]}")
                raise RuntimeError(f"Subtitle burn failed: {sub_result.stderr[-500:]}")

            # Upload to Google Drive if configured, otherwise fallback to local URL
            drive = get_drive_service()
            if drive:
                video_title = data.get("video_title") or project_id
                folder_id = drive.get_or_create_folder(video_title)
                clip_url = drive.upload_clip(final_path, final_filename, folder_id)
                try:
                    os.remove(final_path)
                except Exception as del_err:
                    print(f"[{project_id}] Warning: could not delete local file: {del_err}")
            else:
                clip_url = f"/clips/{project_id}/{final_filename}"

            output_files.append({
                "filename": final_filename,
                "url": clip_url,
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


# ─────────────────────────────────────────────
# Auto-process cron endpoints
# ─────────────────────────────────────────────

@app.post("/api/trigger-process")
async def trigger_process():
    """Manually trigger Cron 1 (auto-process unprocessed videos from sheet)."""
    asyncio.create_task(run_auto_process())
    return {"message": "Auto-process triggered"}


@app.get("/api/cron-status")
def get_cron_status():
    """Check if auto-process cron is currently running."""
    return {
        "running": _cron_running,
        "interval_minutes": CRON_INTERVAL_MINUTES,
        "next_run": str(scheduler.get_job("auto_process").next_run_time) if scheduler.get_job("auto_process") else None,
    }
