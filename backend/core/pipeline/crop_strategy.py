from typing import List, Dict, Optional, Tuple
from core.pipeline.config import HEAD_ROOM_TOP, FACE_PADDING_SIDE


def compute_crop_box(
    faces: List[Dict],
    frame_w: int,
    frame_h: int,
    aspect_ratio: str,
    active_speaker: Optional[str],
    speaker_registry: Dict
) -> Dict:
    """
    Decide crop box based on number of faces detected and aspect ratio.

    Returns:
        {"x": int, "y": int, "w": int, "h": int, "mode": str}
    """
    target_w, target_h = _target_size(frame_w, frame_h, aspect_ratio)

    if len(faces) == 0:
        return _center_crop(frame_w, frame_h, target_w, target_h, mode="center")

    elif len(faces) == 1:
        return _single_face_crop(faces[0], frame_w, frame_h, target_w, target_h)

    elif len(faces) == 2:
        if active_speaker and speaker_registry:
            # Find which face corresponds to active speaker
            speaker_face = _find_speaker_face(faces, active_speaker, speaker_registry)
            if speaker_face:
                return _single_face_crop(speaker_face, frame_w, frame_h, target_w, target_h)
        # Split screen (only for 9:16)
        if aspect_ratio == "9:16":
            return _split_screen_crop(faces, frame_w, frame_h, target_w, target_h)
        else:
            return _multi_face_crop(faces, frame_w, frame_h, target_w, target_h)

    else:
        # 3+ faces — wide/center crop
        return _multi_face_crop(faces, frame_w, frame_h, target_w, target_h)


def _target_size(frame_w: int, frame_h: int, aspect_ratio: str) -> Tuple[int, int]:
    """Compute the crop dimensions to achieve target aspect ratio."""
    if aspect_ratio == "9:16":
        # Crop width from full height
        target_h = frame_h
        target_w = int(frame_h * 9 / 16)
        if target_w > frame_w:
            target_w = frame_w
            target_h = int(frame_w * 16 / 9)
    elif aspect_ratio == "1:1":
        size = min(frame_w, frame_h)
        target_w = target_h = size
    else:  # 16:9
        target_w = frame_w
        target_h = int(frame_w * 9 / 16)
        if target_h > frame_h:
            target_h = frame_h
            target_w = int(frame_h * 16 / 9)
    return target_w, target_h


def _center_crop(frame_w, frame_h, target_w, target_h, mode="center") -> Dict:
    x = (frame_w - target_w) // 2
    y = (frame_h - target_h) // 2
    return {"x": x, "y": y, "w": target_w, "h": target_h, "mode": mode}


def _single_face_crop(face: Dict, frame_w, frame_h, target_w, target_h) -> Dict:
    fx, fy, fw, fh = face["x"], face["y"], face["w"], face["h"]

    # Center of face
    face_cx = fx + fw / 2

    # Add headroom: move crop window up so face has headroom at top
    face_top = fy
    crop_y = int(face_top - target_h * HEAD_ROOM_TOP)
    crop_y = max(0, min(crop_y, frame_h - target_h))

    # Center crop horizontally on face
    crop_x = int(face_cx - target_w / 2)
    crop_x = max(0, min(crop_x, frame_w - target_w))

    return {"x": crop_x, "y": crop_y, "w": target_w, "h": target_h, "mode": "single"}


def _split_screen_crop(faces: List[Dict], frame_w, frame_h, target_w, target_h) -> Dict:
    """For 2 faces, use the center crop that encompasses both."""
    all_x = [f["x"] for f in faces] + [f["x"] + f["w"] for f in faces]
    all_y = [f["y"] for f in faces] + [f["y"] + f["h"] for f in faces]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    crop_x = int(center_x - target_w / 2)
    crop_y = int(center_y - target_h / 2 - target_h * HEAD_ROOM_TOP)
    crop_x = max(0, min(crop_x, frame_w - target_w))
    crop_y = max(0, min(crop_y, frame_h - target_h))

    return {"x": crop_x, "y": crop_y, "w": target_w, "h": target_h, "mode": "split"}


def _multi_face_crop(faces: List[Dict], frame_w, frame_h, target_w, target_h) -> Dict:
    """Wide crop encompassing all faces."""
    all_x = [f["x"] for f in faces] + [f["x"] + f["w"] for f in faces]
    all_y = [f["y"] for f in faces] + [f["y"] + f["h"] for f in faces]
    center_x = (min(all_x) + max(all_x)) / 2
    center_y = (min(all_y) + max(all_y)) / 2

    crop_x = int(center_x - target_w / 2)
    crop_y = int(center_y - target_h / 2)
    crop_x = max(0, min(crop_x, frame_w - target_w))
    crop_y = max(0, min(crop_y, frame_h - target_h))

    return {"x": crop_x, "y": crop_y, "w": target_w, "h": target_h, "mode": "wide"}


def _find_speaker_face(faces: List[Dict], speaker: str, registry: Dict) -> Optional[Dict]:
    """Find the face closest to the registered position for a speaker."""
    if speaker not in registry:
        return None
    reg = registry[speaker]
    best_face = None
    best_dist = float("inf")
    for f in faces:
        cx = f["x"] + f["w"] / 2
        cy = f["y"] + f["h"] / 2
        dist = ((cx - reg["x_center"]) ** 2 + (cy - reg["y_center"]) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_face = f
    return best_face


def interpolate_crops(
    face_detections: List[Dict],
    diarization: List[Dict],
    speaker_registry: Dict,
    frame_w: int,
    frame_h: int,
    total_frames: int,
    fps: float,
    clip_start: float,
    aspect_ratio: str
) -> List[Dict]:
    """
    For each frame in the clip, compute the crop box.
    Uses sampled face detections and interpolates between them.
    """
    # Build timestamp → crop box from sampled frames
    sampled_crops = {}
    for fd in face_detections:
        ts = fd["timestamp"]
        faces = fd["faces"]

        # Find active speaker at this timestamp
        active_speaker = None
        for seg in diarization:
            if seg["start"] <= ts <= seg["end"]:
                active_speaker = seg["speaker"]
                break

        crop = compute_crop_box(faces, frame_w, frame_h, aspect_ratio, active_speaker, speaker_registry)
        sampled_crops[ts] = crop

    if not sampled_crops:
        # Fallback: center crop for all frames
        target_w, target_h = _target_size(frame_w, frame_h, aspect_ratio)
        default_crop = _center_crop(frame_w, frame_h, target_w, target_h)
        return [default_crop] * total_frames

    sorted_times = sorted(sampled_crops.keys())

    # Interpolate to per-frame
    crops_per_frame = []
    for i in range(total_frames):
        ts = clip_start + i / fps

        if ts <= sorted_times[0]:
            crops_per_frame.append(sampled_crops[sorted_times[0]])
        elif ts >= sorted_times[-1]:
            crops_per_frame.append(sampled_crops[sorted_times[-1]])
        else:
            # Linear interpolation between nearest timestamps
            for j in range(len(sorted_times) - 1):
                t0, t1 = sorted_times[j], sorted_times[j + 1]
                if t0 <= ts <= t1:
                    alpha = (ts - t0) / (t1 - t0) if t1 > t0 else 0
                    c0 = sampled_crops[t0]
                    c1 = sampled_crops[t1]
                    crops_per_frame.append({
                        "x": int(c0["x"] + alpha * (c1["x"] - c0["x"])),
                        "y": int(c0["y"] + alpha * (c1["y"] - c0["y"])),
                        "w": int(c0["w"] + alpha * (c1["w"] - c0["w"])),
                        "h": int(c0["h"] + alpha * (c1["h"] - c0["h"])),
                        "mode": c0["mode"]
                    })
                    break
            else:
                crops_per_frame.append(sampled_crops[sorted_times[-1]])

    return crops_per_frame
