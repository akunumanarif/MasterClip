# 🎬 AI Video Shorts Generator

Transform long YouTube videos into viral shorts with AI-powered smart cropping and dynamic captions!

## ✨ Features

- 🎥 **YouTube Download**: Download videos in multiple resolutions (360p - 1080p)
- 🍪 **Cookie Support**: Auto-extract cookies from browser for age-restricted videos
- ✂️ **Smart Cutting**: Cut multiple segments from one video
- 🤖 **AI Reframing**: Auto-detect faces/objects with YOLOv8 for perfect 9:16 crop
- 📝 **Dynamic Subtitles**: Auto-generate karaoke-style animated captions
- 🎨 **Modern UI**: Beautiful Next.js frontend with Tailwind CSS

## 🔧 Tech Stack

### Backend
- **FastAPI** - High-performance Python API
- **yt-dlp** - YouTube video downloader with cookie support
- **FFmpeg** - Video processing
- **OpenCV** - Face detection
- **YOLOv8** - Object detection
- **Whisper** - Speech recognition for subtitles

### Frontend
- **Next.js 15** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Lucide Icons** - Beautiful icons

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install Python 3.10+
python --version

# Install Node.js 18+
node --version

# Install FFmpeg
winget install FFmpeg
```

### 2. Clone & Install

```bash
# Clone repository
git clone <your-repo-url>
cd youtubeClipper

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install
```

### 3. Download YOLOv8 Model

```bash
# Download from root directory
cd ..
# The model will be auto-downloaded on first run, or download manually:
# https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

### 4. Run Development Server

**Option A: Using PowerShell Script (Recommended)**
```powershell
.\start_dev.ps1
```

**Option B: Manual Start**
```bash
# Terminal 1: Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 5. Open Browser

Visit: `http://localhost:3000`

## 🍪 YouTube Cookies Setup

For **age-restricted** or **private videos**, see: [`YOUTUBE_COOKIES_GUIDE.md`](./YOUTUBE_COOKIES_GUIDE.md)

**TL;DR**: The app automatically extracts cookies from Chrome browser. Just make sure you're logged into YouTube in Chrome!

## 📖 Usage

1. **Enter YouTube URL**: Paste any YouTube video link
2. **Select Resolution**: Choose from 360p to 1080p
3. **Add Segments**: Define multiple clip timestamps (HH:MM:SS format)
4. **Generate**: Click "Generate Shorts" and wait for AI processing
5. **Download**: Save your 9:16 vertical shorts!

## 🎯 Example

```
URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
Resolution: 1080p
Segments:
  - Clip 1: 00:00:10 → 00:00:30
  - Clip 2: 00:01:00 → 00:01:20
  
Result: 2 vertical shorts with auto-cropped faces and animated subtitles!
```

## 🧪 Testing

### Test YouTube Download + Cookies

```bash
cd backend
python test_cookies.py
```

This will test:
- ✅ Normal video download
- ✅ Age-restricted video with cookies

## 📁 Project Structure

```
youtubeClipper/
├── backend/
│   ├── core/
│   │   ├── downloader.py        # YouTube download with cookies
│   │   ├── processing.py        # AI face/object detection + reframing
│   │   └── transcription.py     # Whisper subtitles
│   ├── main.py                  # FastAPI endpoints
│   ├── requirements.txt
│   └── test_cookies.py          # Cookie testing script
├── frontend/
│   ├── app/
│   │   └── page.tsx             # Main UI
│   ├── lib/
│   │   └── utils.ts
│   └── package.json
├── output/                      # Generated videos
├── temp/                        # Temporary files
├── yolov8n.pt                   # YOLO model
├── start_dev.ps1                # Dev server launcher
└── YOUTUBE_COOKIES_GUIDE.md     # Cookie setup guide
```

## 🔒 Security

⚠️ **IMPORTANT**: 
- Never commit `youtube_cookies.txt` to Git
- Already added to `.gitignore` for safety
- Cookies contain your YouTube login session

## 🐛 Troubleshooting

### "HTTP Error 403: Forbidden"
- Solution: Enable cookie support (see `YOUTUBE_COOKIES_GUIDE.md`)

### "Sign in to confirm you're not a bot"
- Solution: Login to YouTube in Chrome, then re-run

### Download is slow
- Solution: Lower resolution (720p/480p instead of 1080p)

### YOLOv8 not working
- Solution: `pip install ultralytics` and ensure `yolov8n.pt` exists

## 📝 API Endpoints

### POST `/api/process`
Start video processing

**Request:**
```json
{
  "youtube_url": "https://youtube.com/watch?v=...",
  "segments": [
    {"start_time": "00:00:10", "end_time": "00:00:30"}
  ],
  "resolution": "1080p",
  "cookies_file": null  // Optional: path to cookies file
}
```

**Response:**
```json
{
  "message": "Processing started",
  "project_id": "uuid-here"
}
```

### GET `/api/status/{project_id}`
Check processing status

**Response:**
```json
{
  "status": "completed",
  "message": "All clips processed",
  "outputs": ["uuid_clip1_final.mp4", "uuid_clip2_final.mp4"]
}
```

## 🎨 Features in Detail

### 🤖 AI Smart Crop
- Detects faces using OpenCV Haar Cascade
- Detects objects using YOLOv8 (books, phones, laptops)
- Prioritizes: Person > Held Objects > Center
- Crops to perfect 9:16 (TikTok/Instagram Reels format)

### 📝 Dynamic Subtitles
- Uses OpenAI Whisper for transcription
- Generates ASS format with animations
- Karaoke-style word highlighting
- Professional styling with borders/shadows

### 🎥 Multi-Resolution Support
- **1080p**: Full HD (best quality)
- **720p**: HD (balanced)
- **480p**: SD (fast)
- **360p**: Low (very fast)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloader
- [YOLOv8](https://github.com/ultralytics/ultralytics) - Object detection
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [FFmpeg](https://ffmpeg.org/) - Video processing

---

**Made with ❤️ for content creators**

For detailed cookie setup, see: [`YOUTUBE_COOKIES_GUIDE.md`](./YOUTUBE_COOKIES_GUIDE.md)
