import yt_dlp
import os

def download_youtube_video(url: str, output_dir: str = "temp"):
    """
    Downloads the best quality video from YouTube using yt-dlp.
    Returns the path to the downloaded file.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'noplaylist': True,
        # Workarounds for 403 Forbidden / Signatures
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
            },
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            ext = info['ext']
            return os.path.join(output_dir, f"{video_id}.{ext}")
    except Exception as e:
        print(f"Download Error: {e}")
        raise
