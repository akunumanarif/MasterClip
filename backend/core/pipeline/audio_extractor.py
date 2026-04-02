import subprocess
import os


def extract_audio(video_path: str, output_path: str) -> str:
    """
    Extract mono 16kHz WAV audio from video — optimal for Whisper & Pyannote.
    output_path: full path for the output .wav file.
    Returns output_path.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ac", "1",
        "-ar", "16000",
        "-vn",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr}")
    return output_path
