import whisper
from core.pipeline.config import WHISPER_MODEL

_model = None


def _get_model():
    global _model
    if _model is None:
        print(f"  Loading Whisper model '{WHISPER_MODEL}'...")
        _model = whisper.load_model(WHISPER_MODEL)
    return _model


def transcribe(audio_path: str) -> dict:
    """
    Transcribe audio using openai-whisper with word-level timestamps.

    Returns:
        {
            "language": "id",
            "segments": [...],
            "words": [{"word": str, "start": float, "end": float}, ...]
        }
    """
    model = _get_model()
    print(f"  Transcribing {audio_path}...")
    result = model.transcribe(
        audio_path,
        word_timestamps=True,
        verbose=False
    )

    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": w["start"],
                "end": w["end"]
            })

    return {
        "language": result.get("language", "unknown"),
        "segments": result.get("segments", []),
        "words": words
    }
