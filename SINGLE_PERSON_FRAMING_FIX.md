# Single-Person Framing Fix

## Problem Identified

When video shows **2+ people**, the algorithm was using **median** of all detected faces:

```
[Wajah A]    [Space Kosong]    [Wajah B]
  X=300           X=640           X=980

median([300, 980]) = 640  ← Frames empty space! ❌
```

**Result**: Portrait crop (9:16) bingkai **area kosong** di tengah 2 orang, bukan fokus ke **satu orang spesifik**.

---

## Solution

**Changed from Median to Clustering:**

```python
# ❌ OLD: Median (can fall between people)
result = int(np.median(all_face_positions))

# ✅ NEW: Pick single most consistent position
clustered = [round(x / 50) * 50 for x in face_centers]
position_counts = Counter(clustered)
best_position = position_counts.most_common(1)[0][0]  # Most frequent
```

**Logic:**
1. Cluster nearby positions (50px tolerance)
2. Count frequency of each position
3. Pick position that appears **most consistently** across frames
4. This = **one specific person**, not space between them

---

## Before vs After

### Before (Median):
```
Video: [Person A]  [Space]  [Person B]
Detections: 300, 305, 310, 975, 980, 990
Median: 640  ← Falls in empty space!
Result: ❌ Frame kosong/tangan
```

### After (Clustering):
```
Video: [Person A]  [Space]  [Person B]
Detections: 300, 305, 310, 975, 980, 990

Clusters:
- ~300: 3 occurrences (Person A)
- ~980: 3 occurrences (Person B)

Most common: 300 (tie-break by first)
Result: ✅ Frame Person A
```

---

## Files Changed

**[`backend/core/processing.py`](file:///c:/Users/numan/Documents/Projects/youtubeClipper/backend/core/processing.py)**

1. **Face detection stage** (lines ~190-211)
   - Replaced median with clustering
   
2. **YOLO fallback stage** (lines ~284-296)
   - Replaced median with clustering

**Affected both stages** to ensure consistent behavior!

---

## Testing

Try with multi-person video:
```
URL: https://www.youtube.com/watch?v=Uqb0PD9srbA
Timestamp: 00:02:55 - 00:03:10
```

**Expected:**
- ✅ Frames **ONE specific person** (face centered)
- ✅ NOT empty space between people
- ✅ Consistent across frames (no jumping)

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Multi-person handling | Median (between people) | **Clustering (pick ONE)** |
| Portrait framing | Space kosong | ✅ **Single face** |
| Consistency | Variable | ✅ **Most frequent** position |

**Result**: Portrait videos sekarang **always frame satu orang spesifik**, bukan space kosong! 🎯
