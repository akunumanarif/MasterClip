"""
Test script untuk mengecek apakah cookies YouTube bekerja dengan baik.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.downloader import download_youtube_video

def test_download(url, use_cookies=True):
    """
    Test download video YouTube dengan atau tanpa cookies
    """
    print("="*60)
    print(f"Testing download: {url}")
    print(f"Using cookies: {'Yes (auto-extract from browser)' if use_cookies else 'No'}")
    print("="*60)
    
    try:
        # Test dengan auto-extract cookies dari browser
        video_path = download_youtube_video(
            url=url,
            output_dir="temp",
            resolution="720p",  # 720p untuk test lebih cepat
            cookies_file=None  # None = auto-extract dari browser
        )
        
        print("\n✅ SUCCESS!")
        print(f"Video downloaded to: {video_path}")
        print(f"File size: {os.path.getsize(video_path) / (1024*1024):.2f} MB")
        return True
        
    except Exception as e:
        print("\n❌ FAILED!")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("\n🎬 YouTube Cookies Test Script\n")
    
    # Test 1: Video normal (tidak butuh cookies)
    print("\n📹 Test 1: Normal Video")
    test_download("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Test 2: Video age-restricted (butuh cookies)
    # Ganti dengan URL video yang age-restricted untuk test
    print("\n\n🔞 Test 2: Age-Restricted Video")
    print("⚠️  Pastikan Anda sudah login ke YouTube di browser Chrome!")
    print("⚠️  Ganti URL di bawah dengan video age-restricted untuk test nyata\n")
    
    age_restricted_url = input("Enter age-restricted video URL (or press Enter to skip): ").strip()
    if age_restricted_url:
        test_download(age_restricted_url)
    else:
        print("Skipped age-restricted test")
    
    print("\n\n" + "="*60)
    print("Testing complete!")
    print("="*60)
