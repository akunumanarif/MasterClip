"""
Quick test script to verify face detection is working correctly
"""
import sys
sys.path.append('.')

from core.processing import detect_visual_interest_x
import os

test_video = "temp/Uqb0PD9srbA.mp4"  # The video we downloaded earlier

if not os.path.exists(test_video):
    print(f"❌ Test video not found: {test_video}")
    print("Download a video first using the downloader")
    sys.exit(1)

print("=" * 80)
print("🧪 Testing Face Detection")
print("=" * 80)
print(f"\nVideo: {test_video}\n")

try:
    center_x = detect_visual_interest_x(test_video)
    
    if center_x:
        print(f"\n{'='*80}")
        print(f"✅ SUCCESS! Detected visual center at X = {center_x}")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"⚠️  No detection - will use center crop")
        print(f"{'='*80}")
        
except Exception as e:
    print(f"\n{'='*80}")
    print(f"❌ ERROR: {e}")
    print(f"{'='*80}")
    import traceback
    traceback.print_exc()
