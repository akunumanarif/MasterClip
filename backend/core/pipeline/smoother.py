from typing import List, Dict
import numpy as np
from scipy.ndimage import gaussian_filter1d
from core.pipeline.config import SMOOTHING_SIGMA


def smooth_crops(crops: List[Dict], frame_w: int, frame_h: int) -> List[Dict]:
    """
    Apply Gaussian smoothing to crop trajectory to eliminate jitter.
    Operates on x, y, w, h independently.
    """
    if not crops:
        return crops

    xs = np.array([c["x"] for c in crops], dtype=float)
    ys = np.array([c["y"] for c in crops], dtype=float)
    ws = np.array([c["w"] for c in crops], dtype=float)
    hs = np.array([c["h"] for c in crops], dtype=float)

    # Apply Gaussian smoothing
    sigma = SMOOTHING_SIGMA
    xs_smooth = gaussian_filter1d(xs, sigma=sigma)
    ys_smooth = gaussian_filter1d(ys, sigma=sigma)
    ws_smooth = gaussian_filter1d(ws, sigma=sigma)
    hs_smooth = gaussian_filter1d(hs, sigma=sigma)

    smoothed = []
    for i in range(len(crops)):
        w = int(round(ws_smooth[i]))
        h = int(round(hs_smooth[i]))
        x = int(round(xs_smooth[i]))
        y = int(round(ys_smooth[i]))

        # Clamp to frame bounds
        w = max(1, min(w, frame_w))
        h = max(1, min(h, frame_h))
        x = max(0, min(x, frame_w - w))
        y = max(0, min(y, frame_h - h))

        smoothed.append({
            "x": x, "y": y, "w": w, "h": h,
            "mode": crops[i].get("mode", "center")
        })

    return smoothed
