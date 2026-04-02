from typing import List, Dict


def merge(whisper_words: List[Dict], diarization: List[Dict]) -> List[Dict]:
    """
    Merge Whisper word-level transcription with Pyannote speaker diarization.

    For each word, find which speaker was active at that timestamp.
    Group consecutive words by speaker into segments.

    Returns list of:
        {
            "speaker": "SPEAKER_00",
            "text": "full text",
            "start": float,
            "end": float,
            "words": [{"word", "start", "end"}, ...]
        }
    """
    if not whisper_words:
        return []

    # Assign speaker to each word
    def get_speaker(word_start: float, word_end: float) -> str:
        word_mid = (word_start + word_end) / 2
        best_speaker = "SPEAKER_00"
        best_overlap = 0.0
        for seg in diarization:
            overlap = min(word_end, seg["end"]) - max(word_start, seg["start"])
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = seg["speaker"]
        return best_speaker

    # If no diarization, use single speaker
    if not diarization:
        return _group_into_segments(
            [{"word": w["word"], "start": w["start"], "end": w["end"], "speaker": "SPEAKER_00"}
             for w in whisper_words]
        )

    words_with_speaker = []
    for w in whisper_words:
        speaker = get_speaker(w["start"], w["end"])
        words_with_speaker.append({
            "word": w["word"],
            "start": w["start"],
            "end": w["end"],
            "speaker": speaker
        })

    return _group_into_segments(words_with_speaker)


def _group_into_segments(words: List[Dict]) -> List[Dict]:
    """Group consecutive words by speaker, splitting on pauses > 2s."""
    if not words:
        return []

    segments = []
    current_words = [words[0]]
    current_speaker = words[0]["speaker"]

    for w in words[1:]:
        pause = w["start"] - current_words[-1]["end"]
        if w["speaker"] != current_speaker or pause > 2.0:
            segments.append(_make_segment(current_words, current_speaker))
            current_words = [w]
            current_speaker = w["speaker"]
        else:
            current_words.append(w)

    if current_words:
        segments.append(_make_segment(current_words, current_speaker))

    return segments


def _make_segment(words: List[Dict], speaker: str) -> Dict:
    text = " ".join(w["word"] for w in words).strip()
    return {
        "speaker": speaker,
        "text": text,
        "start": words[0]["start"],
        "end": words[-1]["end"],
        "words": [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in words]
    }
