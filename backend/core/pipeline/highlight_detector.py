from typing import List, Dict
import numpy as np
from core.pipeline.config import (
    CLIP_MIN_DURATION, CLIP_MAX_DURATION, TOP_N_CLIPS, OVERLAP_THRESHOLD
)

_st_model = None

FILLER_WORDS = {"um", "uh", "like", "you know", "so", "basically", "literally",
                "actually", "honestly", "eh", "ah", "hmm", "em", "eeh"}


def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        print("  Loading sentence-transformers model...")
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


def detect_highlights(segments: List[Dict], top_n: int = TOP_N_CLIPS) -> List[Dict]:
    """
    Score segments and return top N clip candidates.

    Each candidate:
        {
            "index": int,
            "start": float,
            "end": float,
            "duration": float,
            "speaker": str,
            "speakers_in_clip": [str],
            "text_preview": str,
            "score": float,
            "word_count": int
        }
    """
    if not segments:
        return []

    # Filter segments too short
    valid = [s for s in segments if (s["end"] - s["start"]) >= 5.0 and len(s["text"].split()) >= 5]
    if not valid:
        valid = segments

    # Build sliding-window clip candidates from consecutive segments
    candidates = _build_candidates(valid)

    if not candidates:
        return []

    # Score each candidate
    scored = _score_candidates(candidates)

    # Non-maximum suppression to avoid overlapping clips
    selected = _nms(scored, overlap_threshold=OVERLAP_THRESHOLD)

    # Sort by score descending, take top N
    selected.sort(key=lambda x: x["score"], reverse=True)
    top = selected[:top_n]

    # Re-index and format
    result = []
    for i, c in enumerate(top):
        result.append({
            "index": i,
            "start": round(c["start"], 2),
            "end": round(c["end"], 2),
            "duration": round(c["end"] - c["start"], 2),
            "speaker": c.get("dominant_speaker", "SPEAKER_00"),
            "speakers_in_clip": sorted(set(c.get("speakers", []))),
            "text_preview": c["text"][:150].strip() + ("..." if len(c["text"]) > 150 else ""),
            "score": round(c["score"], 3),
            "word_count": len(c["text"].split())
        })

    return result


def _build_candidates(segments: List[Dict]) -> List[Dict]:
    """Build clip candidates by finding natural groupings within duration constraints."""
    candidates = []

    for i in range(len(segments)):
        clip_segments = [segments[i]]
        clip_start = segments[i]["start"]
        clip_end = segments[i]["end"]

        # Expand clip by adding following segments
        for j in range(i + 1, len(segments)):
            new_end = segments[j]["end"]
            duration = new_end - clip_start
            if duration > CLIP_MAX_DURATION:
                break
            clip_segments.append(segments[j])
            clip_end = new_end

        duration = clip_end - clip_start
        if duration < CLIP_MIN_DURATION:
            continue

        full_text = " ".join(s["text"] for s in clip_segments)
        speakers = [s["speaker"] for s in clip_segments]
        from collections import Counter
        dominant = Counter(speakers).most_common(1)[0][0]

        candidates.append({
            "start": clip_start,
            "end": clip_end,
            "text": full_text,
            "speakers": speakers,
            "dominant_speaker": dominant,
            "segment_count": len(clip_segments)
        })

    return candidates


def _score_candidates(candidates: List[Dict]) -> List[Dict]:
    """Score candidates using semantic density + length + vocab diversity."""
    if not candidates:
        return []

    texts = [c["text"] for c in candidates]

    # Semantic scoring via sentence embeddings
    try:
        model = _get_st_model()
        embeddings = model.encode(texts, batch_size=16, show_progress_bar=False)
        # Cosine similarity between consecutive candidates for density
        semantic_scores = []
        for i, emb in enumerate(embeddings):
            if len(embeddings) > 1:
                # Average similarity with neighbors
                neighbors = []
                if i > 0:
                    neighbors.append(embeddings[i - 1])
                if i < len(embeddings) - 1:
                    neighbors.append(embeddings[i + 1])
                if neighbors:
                    sims = [float(np.dot(emb, n) / (np.linalg.norm(emb) * np.linalg.norm(n) + 1e-8))
                            for n in neighbors]
                    semantic_scores.append(np.mean(sims))
                else:
                    semantic_scores.append(0.5)
            else:
                semantic_scores.append(0.5)
    except Exception as e:
        print(f"  Semantic scoring failed: {e}, using heuristic only")
        semantic_scores = [0.5] * len(candidates)

    scored = []
    for i, c in enumerate(candidates):
        words = c["text"].split()
        word_count = len(words)

        # Length score (prefer 45-60 second clips)
        duration = c["end"] - c["start"]
        ideal_duration = 55.0
        length_score = 1.0 - min(abs(duration - ideal_duration) / ideal_duration, 1.0)

        # Vocabulary diversity
        unique_words = len(set(w.lower() for w in words))
        diversity_score = min(unique_words / max(word_count, 1), 1.0)

        # Filler word penalty
        filler_count = sum(1 for w in words if w.lower() in FILLER_WORDS)
        filler_penalty = max(0, 1.0 - (filler_count / max(word_count, 1)) * 3)

        # Combined score
        score = (
            semantic_scores[i] * 0.4 +
            length_score * 0.25 +
            diversity_score * 0.25 +
            filler_penalty * 0.1
        )

        scored.append({**c, "score": score})

    return scored


def _nms(candidates: List[Dict], overlap_threshold: float) -> List[Dict]:
    """Non-maximum suppression: remove overlapping clips, keep higher-scored ones."""
    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = []

    for c in candidates:
        overlap = False
        for s in selected:
            # Check overlap ratio
            start = max(c["start"], s["start"])
            end = min(c["end"], s["end"])
            if end > start:
                overlap_duration = end - start
                c_duration = c["end"] - c["start"]
                s_duration = s["end"] - s["start"]
                ratio = overlap_duration / min(c_duration, s_duration)
                if ratio > overlap_threshold:
                    overlap = True
                    break
        if not overlap:
            selected.append(c)

    return selected
