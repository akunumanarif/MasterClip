import os
from typing import List, Dict

_pipeline = None


def _get_pipeline(token: str):
    global _pipeline
    if _pipeline is None:
        from pyannote.audio import Pipeline
        print("  Loading Pyannote speaker diarization pipeline...")
        _pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token
        )
    return _pipeline


def diarize(audio_path: str, token: str) -> List[Dict]:
    """
    Run speaker diarization on audio file.

    Returns list of:
        {"speaker": "SPEAKER_00", "start": float, "end": float}
    """
    if not token:
        print("  No PYANNOTE_AUTH_TOKEN set — skipping diarization.")
        return []

    try:
        pipeline = _get_pipeline(token)
        print(f"  Running diarization on {audio_path}...")
        diarization = pipeline(audio_path)

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "speaker": speaker,
                "start": round(turn.start, 3),
                "end": round(turn.end, 3)
            })
        print(f"  Diarization found {len(set(s['speaker'] for s in segments))} speakers, {len(segments)} segments")
        return segments
    except Exception as e:
        print(f"  Diarization failed: {e}. Proceeding without speaker info.")
        return []
