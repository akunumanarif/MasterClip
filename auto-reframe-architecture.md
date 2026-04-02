# Auto Reframe Video Pipeline — Architecture Plan

## Overview

Pipeline ini dirancang untuk secara otomatis mendeteksi highlight dari video panjang (YouTube, podcast, interview, panel), lalu menghasilkan clip pendek dengan speaker selalu berada di tengah frame. Dioptimasi untuk environment **CPU-only** tanpa GPU.

---

## UX Flow (Two-Phase Pipeline)

```
┌─────────────────────────────────────────────────────────┐
│                   USER INPUT                            │
│   YouTube URL + settings                                │
└──────────────────────────┬──────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   PHASE 1: ANALYZE      │
              │   (Layers 1–5)          │
              │   ~5–15 min for 30min   │
              │   video on CPU          │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   REVIEW STAGE          │
              │   User melihat daftar   │
              │   clip candidates:      │
              │   - Timestamp           │
              │   - Duration            │
              │   - Speaker             │
              │   - Text preview        │
              │   - Relevance score     │
              │                         │
              │   User pilih clip mana  │
              │   yang akan digenerate  │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   PHASE 2: GENERATE     │
              │   (Layers 6–10)         │
              │   Hanya untuk clip      │
              │   yang dipilih          │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   VIDEO OUTPUT          │
              │   9:16 / 1:1 / 16:9     │
              └─────────────────────────┘
```

---

## Stack

| Komponen | Library | Fungsi |
|---|---|---|
| Transkripsi | `openai-whisper` | Transkripsi audio + word-level timestamps |
| Speaker Diarization | `pyannote-audio==3.1.1` | Deteksi siapa bicara kapan |
| Highlight Detection | `sentence-transformers` | Semantic scoring tiap segment |
| Face Detection | `mediapipe` | Bounding box wajah per frame |
| Frame Processing | `opencv-python` | Gaussian smoothing + crop |
| Video Rendering | `ffmpeg-python` | Encode output + mux audio |

---

## Full Pipeline Flow

```
┌─────────────────────────────────────────────────────────┐
│                      VIDEO INPUT                        │
└──────────────────────────┬──────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   1. AUDIO EXTRACTION   │
              │   ffmpeg → audio.wav    │
              └────────────┬────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
┌──────────▼──────────┐       ┌────────────▼────────────┐
│   2. TRANSCRIPTION  │       │  3. DIARIZATION         │
│   openai-whisper    │       │  Pyannote 3.1.1          │
│   → words + timing  │       │  → Speaker A/B/C + time │
└──────────┬──────────┘       └────────────┬────────────┘
           │                               │
           └───────────────┬───────────────┘
                           │
              ┌────────────▼────────────┐
              │   4. MERGE & SEGMENT    │
              │   Gabungkan Whisper +   │
              │   Pyannote              │
              │   → [{speaker, text,    │
              │       start, end}]      │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  5. HIGHLIGHT SCORING   │
              │  Sentence Transformers  │
              │  → Top N candidates     │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐    ← REVIEW STAGE
              │  USER SELECTS CLIPS     │       User pilih
              └────────────┬────────────┘       clip mana
                           │
              ┌────────────▼────────────┐
              │  6. FACE DETECTION      │
              │  MediaPipe              │
              │  (hanya pada selected   │
              │   clips, bukan full     │
              │   video)                │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  7. SPEAKER-FACE        │
              │     MATCHING            │
              │  Heuristic: dominant    │
              │  face di period         │
              │  speaker X = wajah X    │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  8. CROP STRATEGY       │
              │     DECISION            │
              │  (lihat decision tree)  │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  9. GAUSSIAN SMOOTHING  │
              │  scipy                  │
              │  → Smooth crop window   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  10. RENDER OUTPUT      │
              │  OpenCV + FFmpeg        │
              │  → Crop + encode +      │
              │     mux audio           │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │      VIDEO OUTPUT       │
              │  9:16 / 1:1 / 16:9      │
              └─────────────────────────┘
```

---

## API Endpoints

### POST /api/analyze
- **Input**: `youtube_url`, `resolution`, `color_grading`, `top_n_clips`
- **Process**: Download → Extract audio → Transcribe → Diarize → Merge → Score
- **Returns**: `project_id`, `clip_candidates[]`
- **Status flow**: `idle` → `analyzing` → `ready_for_review`

### POST /api/generate
- **Input**: `project_id`, `selected_clip_indices[]`, `color_grading`
- **Process**: Face detection → Matching → Crop → Smooth → Render
- **Returns**: output video files
- **Status flow**: `ready_for_review` → `generating` → `completed`

### GET /api/status/{project_id}
- Returns current status, message, clip candidates (if available), output files (if completed)

---

## Clip Candidate Schema

```json
{
  "index": 0,
  "start": 10.5,
  "end": 52.3,
  "duration": 41.8,
  "speaker": "SPEAKER_00",
  "speakers_in_clip": ["SPEAKER_00", "SPEAKER_01"],
  "text_preview": "First 100 chars of the segment text...",
  "score": 0.85,
  "word_count": 120
}
```

---

## Detail Per Layer

### Layer 1 — Audio Extraction
```
Tool    : ffmpeg
Input   : video.mp4
Output  : audio.wav (16kHz mono, optimal untuk Whisper & Pyannote)
Command : ffmpeg -i input.mp4 -ac 1 -ar 16000 audio.wav
```

### Layer 2 — Transcription (openai-whisper)
```
Tool    : openai-whisper
Model   : base (default, ~74MB) — bisa diubah ke medium/large di config
Output  : list of {word, start, end} + detected language
Catatan : word_timestamps=True untuk alignment ke word-level
```

### Layer 3 — Speaker Diarization (Pyannote)
```
Tool    : pyannote-audio==3.1.1
Auth    : HuggingFace token (gratis, perlu accept terms di HF)
Output  : list of {speaker_id, start, end}
Catatan : Pyannote 3.1.1 (bukan 4.x) — hindari torchcodec dependency
```
> ⚠️ **Token HuggingFace**: Gunakan Read token (bukan Fine-grained).
> Accept model terms di: https://huggingface.co/pyannote/speaker-diarization-3.1
> dan: https://huggingface.co/pyannote/segmentation-3.0

### Layer 4 — Merge & Segment
```
Proses  : Join Whisper words dengan Pyannote speaker timeline
          berdasarkan timestamp overlap
Output  : [{
            speaker: "SPEAKER_00",
            text: "kalimat lengkap",
            start: 12.4,
            end: 18.7,
            words: [{word, start, end}, ...]
          }]
```

### Layer 5 — Highlight Detection (Sentence Transformers)
```
Tool    : sentence-transformers
Model   : all-MiniLM-L6-v2 (ringan, ~80MB, CPU-friendly)
Proses  :
  1. Embed tiap segment teks
  2. Hitung semantic density score:
     - Cosine similarity antar segment (contextual richness)
     - Panjang segment (hindari segment terlalu pendek)
     - Keragaman vocabulary (hindari filler words)
  3. Sliding window scoring untuk deteksi "peak moments"
  4. Filter berdasarkan min/max durasi clip yang diinginkan
  5. Non-maximum suppression untuk hindari clip overlap

Output  : Top N segment dengan {start, end, score, speaker, text}

Parameter yang bisa dikonfigurasi:
  - clip_min_duration  : default 30 detik
  - clip_max_duration  : default 90 detik
  - top_n_clips        : jumlah clip yang dihasilkan
  - overlap_threshold  : max overlap antar clip (default 0.3)
```

### Layer 6 — Face Detection (MediaPipe)
```
Tool    : mediapipe (Face Detection solution)
Strategi: Proses hanya frames di dalam selected clips
          → hemat waktu vs proses full video

Sampling: Tidak perlu tiap frame — sample setiap N frame
          (default: setiap 5 frame = 6fps equivalent)

Output per frame: [{
  face_id,
  bbox: {x, y, width, height},
  confidence,
  timestamp
}]
```

### Layer 7 — Speaker-Face Matching (Heuristic)
```
Masalah : Pyannote tahu siapa bicara (audio), MediaPipe tahu
          ada wajah di mana (visual), tapi tidak ada link langsung.

Solusi  : Heuristic matching
  1. Untuk tiap speaker segment dari Pyannote,
     kumpulkan semua face detections dalam timerange tersebut
  2. Wajah yang paling sering muncul = kandidat speaker tersebut
  3. Konsistensi posisi: wajah yang posisinya stabil lebih diprioritaskan
  4. Build speaker-face registry: {speaker_id → typical_bbox_region}

Limitasi: Tidak 100% akurat jika 2 orang selalu muncul bersamaan
```

### Layer 8 — Crop Strategy Decision Tree

```
Frame diterima
      │
      ▼
Berapa wajah terdeteksi?
      │
      ├── 0 wajah ──────────────────► CENTER CROP (static)
      │
      ├── 1 wajah ──────────────────► SINGLE SPEAKER CROP
      │                                 Center pada wajah
      │                                 + padding (head room)
      │
      ├── 2 wajah ──────────────────► Cek active speaker?
      │                                    │
      │                               ┌────┴────┐
      │                               │ Ya      │ Tidak
      │                               ▼         ▼
      │                          SINGLE      SPLIT-SCREEN
      │                          SPEAKER     (dua wajah
      │                          CROP        side by side)
      │
      └── 3+ wajah ─────────────────► CENTER/WIDE CROP
```

### Layer 9 — Gaussian Smoothing
```
Tool    : scipy.ndimage.gaussian_filter1d
Tujuan  : Hilangkan jitter pada pergerakan crop window

Proses  :
  1. Kumpulkan semua crop box coordinates sebagai time series
  2. Apply Gaussian smoothing pada x, y, width, height
  3. Kernel size: sigma=15 untuk video 30fps
  4. Clip coordinates agar tidak keluar batas frame
```

### Layer 10 — Video Rendering
```
Tool    : OpenCV (frame reading) + FFmpeg (encoding)

Proses  :
  1. Baca clip dari video original menggunakan cv2
  2. Per frame: apply crop coordinates dari Layer 9
  3. Resize ke target resolution (1080x1920 untuk 9:16)
  4. Pipe ke FFmpeg untuk encoding libx264
  5. Mux dengan audio original (aac)

Encoding: libx264, crf=23, preset=medium
```

---

## Crop Padding & Framing Rules

```
Untuk Single Speaker:
  - Head room atas  : 15% dari tinggi crop box
  - Padding kiri/kanan : 25% dari lebar wajah di tiap sisi
  - Minimum crop size  : 30% dari frame original
  - Maximum crop size  : 100%

Untuk Split Screen (9:16):
  - Frame dibagi vertikal menjadi 2 bagian sama rata
  - Tiap bagian: 1 speaker di-center secara horizontal
```

---

## Estimasi Performa (CPU-Only)

| Stage | Estimasi Waktu | Catatan |
|---|---|---|
| Audio extraction | ~5 detik | Sangat cepat |
| Whisper (base) | ~0.5–1x durasi video | Jauh lebih cepat dari medium |
| Pyannote | ~0.5–1x durasi video | Cukup cepat |
| Sentence Transformers | ~10–30 detik | Ringan |
| Face detection (sampled, selected clips only) | ~0.5x durasi highlight | Hanya selected clips |
| Render | ~0.5x durasi output | OpenCV + FFmpeg |

**Total estimasi** untuk video 30 menit, memilih 3 dari 5 clip candidates:
→ Phase 1 (analyze): ~30–45 menit
→ Phase 2 (generate 3 clips): ~20–40 menit

---

## Project Structure

```
backend/
├── core/
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── audio_extractor.py       # Layer 1
│   │   ├── transcriber.py           # Layer 2 - openai-whisper
│   │   ├── diarizer.py              # Layer 3 - Pyannote 3.1.1
│   │   ├── segment_merger.py        # Layer 4
│   │   ├── highlight_detector.py    # Layer 5 - Sentence Transformers
│   │   ├── face_detector.py         # Layer 6 - MediaPipe
│   │   ├── speaker_matcher.py       # Layer 7
│   │   ├── crop_strategy.py         # Layer 8
│   │   ├── smoother.py              # Layer 9 - scipy
│   │   └── renderer.py              # Layer 10 - OpenCV + FFmpeg
│   ├── downloader.py
│   ├── email_service.py
│   ├── processing.py
│   └── transcription.py
└── main.py
```

---

## Dependencies

```txt
--extra-index-url https://download.pytorch.org/whl/cpu
torch
torchaudio
fastapi
uvicorn
python-multipart
yt-dlp
ffmpeg-python
openai-whisper
opencv-python-headless
mediapipe
Pillow
requests
deep-translator
python-dotenv
pyannote.audio==3.1.1
sentence-transformers
scipy
numpy
```

---

## Config (`pipeline/config.py`)

```python
WHISPER_MODEL = "base"          # base / small / medium
CLIP_MIN_DURATION = 30          # detik
CLIP_MAX_DURATION = 90          # detik
TOP_N_CLIPS = 5
OVERLAP_THRESHOLD = 0.3
FACE_SAMPLE_EVERY_N_FRAMES = 5
FACE_CONFIDENCE_THRESHOLD = 0.7
SMOOTHING_SIGMA = 15
HEAD_ROOM_TOP = 0.15
FACE_PADDING_SIDE = 0.25
DEFAULT_ASPECT_RATIO = "9:16"
OUTPUT_RESOLUTION = {
    "9:16": (1080, 1920),
    "1:1":  (1080, 1080),
    "16:9": (1920, 1080),
}
VIDEO_CRF = 23
VIDEO_PRESET = "medium"
```

---

## Edge Cases & Fallback

| Kondisi | Fallback |
|---|---|
| Tidak ada wajah terdeteksi | Static center crop |
| 3+ wajah dalam frame | Wide shot / center crop |
| Speaker match confidence rendah | Split-screen jika 2 wajah |
| Segment terlalu pendek (<5 detik) | Skip |
| Audio noise (Pyannote gagal) | Fallback ke Whisper speaker labels |
| Crop window keluar batas frame | Clamp ke batas frame |
| Diarization token tidak tersedia | Skip diarization, pakai whisper only |
