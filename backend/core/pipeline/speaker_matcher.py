from typing import List, Dict
from collections import defaultdict, Counter


def match_speakers_to_faces(
    face_detections: List[Dict],
    diarization: List[Dict]
) -> Dict[str, Dict]:
    """
    Heuristic matching: for each speaker segment from diarization,
    find the dominant face in that time range.

    Returns:
        {
            "SPEAKER_00": {"x_center": float, "y_center": float, "region": "left"|"right"|"center"},
            ...
        }
    """
    if not diarization or not face_detections:
        return {}

    # Build face lookup by timestamp
    face_by_time = {fd["timestamp"]: fd["faces"] for fd in face_detections}
    timestamps = sorted(face_by_time.keys())

    speaker_face_data = defaultdict(list)

    for dia_seg in diarization:
        speaker = dia_seg["speaker"]
        seg_start = dia_seg["start"]
        seg_end = dia_seg["end"]

        # Find face detections within this speaker's segment
        relevant_times = [t for t in timestamps if seg_start <= t <= seg_end]
        for t in relevant_times:
            faces = face_by_time[t]
            if len(faces) == 1:
                # Single face during this speaker's turn — strong signal
                f = faces[0]
                cx = f["x"] + f["w"] / 2
                cy = f["y"] + f["h"] / 2
                speaker_face_data[speaker].append({"cx": cx, "cy": cy, "face": f})

    registry = {}
    for speaker, face_list in speaker_face_data.items():
        if not face_list:
            continue
        # Average position
        avg_cx = sum(f["cx"] for f in face_list) / len(face_list)
        avg_cy = sum(f["cy"] for f in face_list) / len(face_list)

        # Determine region (for split-screen logic)
        # This requires knowing frame width — use relative position
        face_sizes = [f["face"]["w"] * f["face"]["h"] for f in face_list]
        avg_size = sum(face_sizes) / len(face_sizes)

        registry[speaker] = {
            "x_center": avg_cx,
            "y_center": avg_cy,
            "avg_size": avg_size,
            "sample_count": len(face_list)
        }

    return registry
