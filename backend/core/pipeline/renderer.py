import cv2
import subprocess
import os
import numpy as np
from typing import List, Dict, Tuple
from core.pipeline.config import (
    OUTPUT_RESOLUTION, VIDEO_CRF, VIDEO_PRESET, VIDEO_CODEC,
    AUDIO_CODEC, AUDIO_BITRATE
)
from core.pipeline.face_detector import detect_faces_in_clip, get_video_info
from core.pipeline.speaker_matcher import match_speakers_to_faces
from core.pipeline.crop_strategy import interpolate_crops
from core.pipeline.smoother import smooth_crops


def render_clip(
    video_path: str,
    audio_path: str,
    clip_start: float,
    clip_end: float,
    output_path: str,
    diarization: List[Dict],
    aspect_ratio: str = "9:16",
    color_grading: str = "none"
) -> str:
    """
    Full render pipeline for a single clip:
    1. Detect faces (sampled)
    2. Match speakers to faces
    3. Compute crop trajectory
    4. Smooth trajectory
    5. Render with OpenCV + FFmpeg
    """
    frame_w, frame_h, fps = get_video_info(video_path)
    out_w, out_h = OUTPUT_RESOLUTION.get(aspect_ratio, (1080, 1920))

    print(f"    Face detection {clip_start:.1f}s–{clip_end:.1f}s...")
    face_detections = detect_faces_in_clip(video_path, clip_start, clip_end)

    print(f"    Speaker-face matching...")
    # Filter diarization to clip range
    clip_diarization = [
        seg for seg in diarization
        if seg["end"] > clip_start and seg["start"] < clip_end
    ]
    speaker_registry = match_speakers_to_faces(face_detections, clip_diarization)

    total_frames = int((clip_end - clip_start) * fps)
    print(f"    Computing crop trajectory ({total_frames} frames)...")
    crops = interpolate_crops(
        face_detections, clip_diarization, speaker_registry,
        frame_w, frame_h, total_frames, fps, clip_start, aspect_ratio
    )

    print(f"    Smoothing crop trajectory...")
    crops = smooth_crops(crops, frame_w, frame_h)

    print(f"    Rendering {len(crops)} frames → {output_path}...")
    _render_frames(
        video_path, audio_path, crops, fps,
        clip_start, clip_end, frame_w, frame_h,
        out_w, out_h, output_path, color_grading
    )

    return output_path


def _render_frames(
    video_path: str,
    audio_path: str,
    crops: List[Dict],
    fps: float,
    clip_start: float,
    clip_end: float,
    frame_w: int,
    frame_h: int,
    out_w: int,
    out_h: int,
    output_path: str,
    color_grading: str
):
    """
    Decode frames via ffmpeg pipe (handles AV1, HEVC, any codec),
    apply per-frame crop in Python, encode output via ffmpeg.
    """
    # --- Decoder: ffmpeg → raw BGR frames ---
    decode_cmd = [
        "ffmpeg",
        "-ss", str(clip_start),
        "-to", str(clip_end),
        "-i", video_path,
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-an",          # no audio on decode side
        "-"             # output to stdout
    ]
    decoder = subprocess.Popen(
        decode_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    # --- Encoder: raw BGR frames → output file ---
    vf = _get_color_filter(color_grading)
    encode_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{out_w}x{out_h}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "pipe:0",          # video from stdin
        "-ss", str(clip_start),
        "-to", str(clip_end),
        "-i", audio_path,        # audio from file
        "-c:v", VIDEO_CODEC,
        "-crf", str(VIDEO_CRF),
        "-preset", VIDEO_PRESET,
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
    ]
    if vf:
        encode_cmd += ["-vf", vf]
    encode_cmd.append(output_path)

    encoder = subprocess.Popen(
        encode_cmd,
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    frame_size = frame_w * frame_h * 3  # BGR24
    frame_count = 0
    total_frames = len(crops)

    try:
        while frame_count < total_frames:
            raw = decoder.stdout.read(frame_size)
            if len(raw) < frame_size:
                break  # end of stream

            frame = np.frombuffer(raw, dtype=np.uint8).reshape((frame_h, frame_w, 3))

            if frame_count < len(crops):
                crop = crops[frame_count]
                x = max(0, min(int(crop["x"]), frame_w - 1))
                y = max(0, min(int(crop["y"]), frame_h - 1))
                w = max(1, min(int(crop["w"]), frame_w - x))
                h = max(1, min(int(crop["h"]), frame_h - y))
            else:
                # fallback: center crop
                x, y, w, h = 0, 0, frame_w, frame_h

            cropped = frame[y:y+h, x:x+w]
            resized = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LINEAR)

            try:
                encoder.stdin.write(resized.tobytes())
            except BrokenPipeError:
                break

            frame_count += 1

    finally:
        decoder.stdout.close()
        decoder.wait()
        try:
            encoder.stdin.close()
        except Exception:
            pass
        encoder.wait()

    print(f"    Rendered {frame_count} frames")


def _get_color_filter(preset: str) -> str:
    presets = {
        "none": "",
        "cinematic_warm": "eq=contrast=1.15:brightness=0.03:saturation=1.2:gamma=1.1",
        "cool_modern": "eq=contrast=1.2:saturation=0.85:gamma_b=0.9:gamma_r=1.1",
        "vibrant": "eq=contrast=1.25:saturation=1.4:brightness=0.05:gamma=1.05",
        "matte_film": "eq=contrast=0.85:saturation=0.8:gamma=1.15:brightness=0.05",
        "bw_contrast": "hue=s=0,eq=contrast=1.35:brightness=0.03:gamma=0.95",
    }
    return presets.get(preset, "")
