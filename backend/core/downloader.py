import yt_dlp
import os

def download_youtube_video(url: str, output_dir: str = "temp", resolution: str = "1080p", cookies_file: str = None):
    """
    Downloads video from YouTube using yt-dlp with specified resolution.
    
    Args:
        url: YouTube video URL
        output_dir: Directory to save downloaded video
        resolution: Target resolution ('1080p', '720p', '480p', '360p')
        cookies_file: Path to cookies file (Netscape format) for authentication.
                     If None, will try to use browser cookies automatically.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Parse target height
    target_height = 1080
    if resolution == "720p": target_height = 720
    elif resolution == "480p": target_height = 480
    elif resolution == "360p": target_height = 360
    
    # SIMPLIFIED & ROBUST Format Selection
    # Strategy: Try to respect resolution preference, but ALWAYS fallback to 'best'
    # This guarantees the download will never fail due to format unavailability
    #
    # Format priority:
    # 1. Try to get video+audio with height limit
    # 2. If that fails, just get the best available format
    #
    # Note: Some videos don't have separate video/audio streams at specific heights,
    # so we must have a simple 'best' fallback
    
    format_str = f'bestvideo[height<={target_height}]+bestaudio/bestvideo+bestaudio/best'
    
    print(f"📥 Downloading with format: {format_str}")
    
    ydl_opts = {
        'format': format_str,
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'noplaylist': True,
        'merge_output_format': 'mp4', # Force output to be MP4
        # User agent for better compatibility
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        # REMOVED player_client args - they can cause format issues
        # Let yt-dlp use its default client selection (more reliable)
    }
    
    # Add cookies support with smart detection and validation
    # Priority:
    # 1. Try with explicit cookies_file (if provided and valid)
    # 2. Try with auto-detected youtube_cookies.txt (if valid)
    # 3. Download without cookies
    
    cookies_to_use = None
    
    if cookies_file and os.path.exists(cookies_file):
        cookies_to_use = cookies_file
    else:
        # Auto-detect youtube_cookies.txt in backend folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(script_dir)
        auto_cookies_path = os.path.join(backend_dir, 'youtube_cookies.txt')
        
        if os.path.exists(auto_cookies_path):
            cookies_to_use = auto_cookies_path
    
    # Try with cookies first (if available)
    if cookies_to_use:
        try:
            print(f"✓ Found cookies file: {os.path.basename(cookies_to_use)}")
            ydl_opts_with_cookies = ydl_opts.copy()
            ydl_opts_with_cookies['cookiefile'] = cookies_to_use
            
            # OPTIMIZATION: Do a quick format check without full extraction
            # This validates cookies without downloading twice
            print(f"🔍 Validating cookies...")
            with yt_dlp.YoutubeDL(ydl_opts_with_cookies) as ydl:
                # Quick check: extract_info with download=False is fast
                info_check = ydl.extract_info(url, download=False)
                
                # Validate that we got actual video formats, not just images
                formats = info_check.get('formats', [])
                has_video = any(f.get('vcodec') != 'none' and f.get('vcodec') != None for f in formats)
                
                if not has_video:
                    print("⚠️  WARNING: Cookies returned no video formats (only images)!")
                    print("   This means cookies are CORRUPT or EXPIRED.")
                    print("   Retrying WITHOUT cookies...")
                    raise Exception("Corrupt/expired cookies - retry without")
                
                # Cookies are good, proceed with download using validated session
                print(f"✅ Cookies valid! Downloading...")
                
            # Download with the validated cookies (reuse session info)
            with yt_dlp.YoutubeDL(ydl_opts_with_cookies) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info['id']
                ext = info['ext']
                final_path = os.path.join(output_dir, f"{video_id}.{ext}")
                print(f"✅ Download complete: {os.path.basename(final_path)}")
                return final_path
                
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  Cookie attempt failed: {error_msg}")
            print("🔄 Retrying WITHOUT cookies...")
            # Fall through to try without cookies
    else:
        print("ℹ  No cookies file found")
    
    # Try WITHOUT cookies (fallback or primary method)
    try:
        print(f"🎬 Extracting video info (without cookies)...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            ext = info['ext']
            final_path = os.path.join(output_dir, f"{video_id}.{ext}")
            print(f"✅ Download complete: {os.path.basename(final_path)}")
            return final_path
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Download Error: {error_msg}")
        
        # Provide helpful error messages
        if "Requested format is not available" in error_msg:
            print("\n💡 Troubleshooting tips:")
            print("   1. Try a different resolution (720p or 480p)")
            print("   2. Update yt-dlp: pip install -U yt-dlp")
        elif "age" in error_msg.lower() or "sign in" in error_msg.lower() or "restricted" in error_msg.lower():
            print("\n🔐 This video requires FRESH cookies:")
            print("   1. Delete old youtube_cookies.txt from backend folder")
            print("   2. Install 'Get cookies.txt LOCALLY' browser extension")
            print("   3. Login to YouTube in browser (logout first if already logged in)")
            print("   4. Export FRESH cookies and save as backend/youtube_cookies.txt")
            print("   5. Restart server")
        
        raise



