"""
Debug script to check available formats for a YouTube video
"""
import yt_dlp
import sys

def check_available_formats(url):
    """
    List all available formats for a YouTube video
    """
    print("=" * 80)
    print(f"🔍 Checking available formats for: {url}")
    print("=" * 80)
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
            },
        },
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            print(f"\n📹 Video: {info.get('title', 'Unknown')}")
            print(f"⏱️  Duration: {info.get('duration', 0)} seconds")
            print(f"👁️  Views: {info.get('view_count', 0):,}")
            
            formats = info.get('formats', [])
            
            print(f"\n📊 Available Formats: {len(formats)} total\n")
            print("-" * 80)
            print(f"{'ID':<10} {'Extension':<10} {'Resolution':<15} {'FPS':<5} {'Codec':<15} {'Size (MB)':<12}")
            print("-" * 80)
            
            # Filter and display relevant formats
            video_formats = []
            audio_formats = []
            
            for f in formats:
                format_id = f.get('format_id', 'N/A')
                ext = f.get('ext', 'N/A')
                resolution = f.get('resolution', 'audio only' if f.get('vcodec') == 'none' else 'N/A')
                fps = f.get('fps', 0) or 0
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                filesize = f.get('filesize') or f.get('filesize_approx') or 0
                filesize_mb = filesize / (1024 * 1024) if filesize else 0
                
                codec_str = vcodec if vcodec != 'none' else acodec
                
                if vcodec != 'none' and acodec == 'none':
                    # Video only
                    video_formats.append(f)
                    print(f"{format_id:<10} {ext:<10} {resolution:<15} {fps:<5.0f} {codec_str:<15} {filesize_mb:<12.2f}")
                elif vcodec == 'none' and acodec != 'none':
                    # Audio only
                    audio_formats.append(f)
                elif vcodec != 'none' and acodec != 'none':
                    # Combined
                    print(f"{format_id:<10} {ext:<10} {resolution:<15} {fps:<5.0f} {codec_str:<15} {filesize_mb:<12.2f} (combined)")
            
            print("-" * 80)
            print(f"\n✅ Video-only streams: {len(video_formats)}")
            print(f"✅ Audio-only streams: {len(audio_formats)}")
            
            # Show best formats
            if video_formats:
                best_1080 = [f for f in video_formats if f.get('height', 0) <= 1080]
                best_720 = [f for f in video_formats if f.get('height', 0) <= 720]
                
                print(f"\n🎯 Best formats <= 1080p: {len(best_1080)}")
                print(f"🎯 Best formats <= 720p: {len(best_720)}")
            
            # Test our format string
            print("\n" + "=" * 80)
            print("🧪 Testing Our Format Selection String")
            print("=" * 80)
            
            test_resolutions = ['1080p', '720p', '480p', '360p']
            
            for res in test_resolutions:
                target_height = int(res.replace('p', ''))
                format_str = (
                    f'bestvideo[height<={target_height}]+bestaudio/'
                    f'bestvideo+bestaudio/'
                    f'best[height<={target_height}]/'
                    f'best'
                )
                
                print(f"\n{res} format string:")
                print(f"  {format_str}")
                
                # Try extracting with this format
                test_opts = ydl_opts.copy()
                test_opts['format'] = format_str
                
                try:
                    with yt_dlp.YoutubeDL(test_opts) as test_ydl:
                        test_info = test_ydl.extract_info(url, download=False)
                        selected_format = test_info.get('format_id', 'Unknown')
                        selected_ext = test_info.get('ext', 'Unknown')
                        selected_height = test_info.get('height', 'Unknown')
                        print(f"  ✅ Would select: format {selected_format} ({selected_ext}, {selected_height}p)")
                except Exception as e:
                    print(f"  ❌ Error: {str(e)}")
            
            print("\n" + "=" * 80)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default test video (the one that failed)
        url = "https://www.youtube.com/watch?v=Uqb0PD9srbA"
        print(f"No URL provided, using default: {url}\n")
    
    check_available_formats(url)
