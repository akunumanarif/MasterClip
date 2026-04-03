from typing import List, Dict, Tuple
import cv2
import numpy as np
import subprocess
import json
from core.pipeline.config import FACE_SAMPLE_EVERY_N_FRAMES, FACE_CONFIDENCE_THRESHOLD

_detector = None


def _get_detector():
    global _detector
    if _detector is None:
        # OpenCV built-in Haar cascade — no extra downloads, no mediapipe version issues
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _detector = cv2.CascadeClassifier(cascade_path)
        if _detector.empty():
            raise RuntimeError(f"Failed to load Haar cascade from {cascade_path}")
    return _detector


def detect_faces_in_clip(
    video_path: str,
    clip_start: float,
    clip_end: float
) -> List[Dict]:
    """
    Detect faces in a clip segment via ffmpeg-decoded frames (supports AV1/HEVC/any codec),
    sampling every N frames using Haar cascade.

    Returns list of:
        {
            "timestamp": float,
            "frame_idx": int,
            "faces": [{"x": int, "y": int, "w": int, "h": int, "confidence": float}]
        }
    """
    frame_w, frame_h, fps = get_video_info(video_path)
    frame_size = frame_w * frame_h * 3  # BGR24

    # Decode clip via ffmpeg — handles all codecs
    decode_cmd = [
        "ffmpeg",
        "-ss", str(clip_start),
        "-to", str(clip_end),
        "-i", video_path,
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-an",
        "-"
    ]
    decoder = subprocess.Popen(
        decode_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    detector = _get_detector()
    results = []
    frame_idx = 0

    try:
        while True:
            raw = decoder.stdout.read(frame_size)
            if len(raw) < frame_size:
                break

            if frame_idx % FACE_SAMPLE_EVERY_N_FRAMES == 0:
                timestamp = clip_start + frame_idx / fps
                frame = np.frombuffer(raw, dtype=np.uint8).reshape((frame_h, frame_w, 3))
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                detections = detector.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(60, 60),
                    flags=cv2.CASCADE_SCALE_IMAGE
                )

                faces = []
                if len(detections) > 0:
                    for (x, y, w, h) in detections:
                        x = max(0, int(x))
                        y = max(0, int(y))
                        w = min(int(w), frame_w - x)
                        h = min(int(h), frame_h - y)
                        faces.append({
                            "x": x, "y": y, "w": w, "h": h,
                            "confidence": 1.0
                        })

                results.append({
                    "timestamp": round(timestamp, 3),
                    "frame_idx": frame_idx,
                    "faces": faces
                })

            frame_idx += 1
    finally:
        decoder.stdout.close()
        decoder.wait()

    return results


def get_video_info(video_path: str) -> Tuple[int, int, float]:
    """Returns (width, height, fps) using ffprobe — works for all codecs including AV1."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-select_streams", "v:0",
                video_path
            ],
            capture_output=True, text=True, check=True
        )
        info = json.loads(result.stdout)
        stream = info["streams"][0]
        w = int(stream["width"])
        h = int(stream["height"])
        # fps can be "30000/1001" format
        fps_raw = stream.get("r_frame_rate", "30/1")
        num, den = fps_raw.split("/")
        fps = float(num) / float(den)
        return w, h, fps
    except Exception as e:
        print(f"  ffprobe failed ({e}), falling back to OpenCV")
        cap = cv2.VideoCapture(video_path)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.release()
        return w, h, fps
