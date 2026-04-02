import os

# Whisper model size: tiny/base/small/medium/large
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Clip detection settings
CLIP_MIN_DURATION = 30      # seconds
CLIP_MAX_DURATION = 90      # seconds
TOP_N_CLIPS = 5
OVERLAP_THRESHOLD = 0.3     # max overlap ratio between clips

# Face detection
FACE_SAMPLE_EVERY_N_FRAMES = 5
FACE_CONFIDENCE_THRESHOLD = 0.6

# Gaussian smoothing for crop trajectory
SMOOTHING_SIGMA = 15

# Framing rules
HEAD_ROOM_TOP = 0.15        # 15% headroom above face
FACE_PADDING_SIDE = 0.25    # 25% padding each side of face

# Output
DEFAULT_ASPECT_RATIO = "9:16"
OUTPUT_RESOLUTION = {
    "9:16": (1080, 1920),
    "1:1":  (1080, 1080),
    "16:9": (1920, 1080),
}

# FFmpeg encoding
VIDEO_CRF = 23
VIDEO_PRESET = "medium"
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"
