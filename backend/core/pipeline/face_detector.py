from typing import List, Dict, Tuple
import cv2
import numpy as np
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
    Detect faces in a clip segment using OpenCV Haar cascade, sampling every N frames.

    Returns list of:
        {
            "timestamp": float,
            "frame_idx": int,
            "faces": [{"x": int, "y": int, "w": int, "h": int, "confidence": float}]
        }
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    start_frame = int(clip_start * fps)
    end_frame = int(clip_end * fps)

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    detector = _get_detector()
    results = []
    frame_idx = start_frame

    while frame_idx <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break

        if (frame_idx - start_frame) % FACE_SAMPLE_EVERY_N_FRAMES == 0:
            timestamp = frame_idx / fps
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # scaleFactor=1.1, minNeighbors=5 — balanced speed/accuracy
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
                    # Clamp to frame bounds
                    x = max(0, int(x))
                    y = max(0, int(y))
                    w = min(int(w), frame_w - x)
                    h = min(int(h), frame_h - y)
                    faces.append({
                        "x": x, "y": y, "w": w, "h": h,
                        "confidence": 1.0  # Haar cascade doesn't provide per-detection scores
                    })

            results.append({
                "timestamp": round(timestamp, 3),
                "frame_idx": frame_idx,
                "faces": faces
            })

        frame_idx += 1

    cap.release()
    return results


def get_video_info(video_path: str) -> Tuple[int, int, float]:
    """Returns (width, height, fps)."""
    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    return w, h, fps
