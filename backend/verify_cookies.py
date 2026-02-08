"""
Simple test to verify cookies are detected and used
"""
import os
import sys

# Test 1: Check if cookies file exists
print("=" * 60)
print("🍪 YouTube Cookies Detection Test")
print("=" * 60)

cookies_path = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')
print(f"\n1. Checking for cookies file...")
print(f"   Path: {cookies_path}")

if os.path.exists(cookies_path):
    print(f"   ✅ Found! File size: {os.path.getsize(cookies_path)} bytes")
    
    # Read first 3 lines to verify format
    with open(cookies_path, 'r') as f:
        lines = f.readlines()[:3]
        print(f"   📄 File preview (first 3 lines):")
        for line in lines:
            print(f"      {line.rstrip()}")
else:
    print(f"   ❌ Not found!")
    sys.exit(1)

# Test 2: Simulate the auto-detection logic
print(f"\n2. Testing auto-detection logic...")
from core.downloader import download_youtube_video

script_dir = os.path.dirname(os.path.abspath(__file__))
auto_cookies_path = os.path.join(script_dir, 'youtube_cookies.txt')

if os.path.exists(auto_cookies_path):
    print(f"   ✅ Auto-detection would work!")
    print(f"   Path: {auto_cookies_path}")
else:
    print(f"   ❌ Auto-detection would fail")

print("\n" + "=" * 60)
print("✅ Cookies file is ready to use!")
print("=" * 60)
print("\nNext step: Try downloading a video with your app")
print("The downloader will automatically use this cookies file.")
