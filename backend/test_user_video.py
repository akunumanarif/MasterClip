"""
Test face detection on user's specific video segment
"""
import sys
sys.path.append('.')

from core.processing import extract_highlight, auto_reframe, detect_visual_interest_x
import os

print("=" * 80)
print("🎬 Testing Face Detection - User's Video")
print("=" * 80)

# Extract the specific segment
input_video = "temp/17fPOe9H5mY.mp4"
clip_path = "temp/test_clip_00_02_19_to_00_02_57.mp4"

print(f"\n📹 Extracting clip: 00:02:19 - 00:02:57")
extract_highlight(input_video, "00:02:19", "00:02:57", clip_path)
print(f"✅ Clip extracted: {clip_path}")

print(f"\n{'='*80}")
print("🔍 Running Face Detection Analysis")
print(f"{'='*80}\n")

# Analyze face detection
tracking_data = detect_visual_interest_x(clip_path)

if tracking_data and 'trajectory' in tracking_data:
    print(f"\n{'='*80}")
    print(f"✅ RESULT: Dynamic trajectory created!")
    
    trajectory = tracking_data['trajectory']
    width = tracking_data['width']
    height = tracking_data['height']
    method = tracking_data.get('method', 'unknown')
    confidence = tracking_data.get('confidence', 0)
    
    # Calculate average position
    avg_x = sum(trajectory.values()) / len(trajectory)
    min_x = min(trajectory.values())
    max_x = max(trajectory.values())
    
    print(f"Video dimensions: {width}x{height}")
    print(f"Tracking method: {method} (confidence={confidence:.2f})")
    print(f"Trajectory frames: {len(trajectory)}")
    print(f"Position range: X={min_x} to {max_x} (movement: {max_x-min_x}px)")
    print(f"Average position: X={avg_x:.0f} ({(avg_x/width)*100:.1f}% from left)")
    
    print(f"{'='*80}\n")
    
    # Now do full reframe with dynamic tracking
    print(f"🎨 Creating 9:16 reframed output with DYNAMIC TRACKING...")
    output_path = "output/test_reframe_result.mp4"
    auto_reframe(clip_path, output_path)
    
    print(f"\n{'='*80}")
    print(f"✅ SUCCESS! Output saved to: {output_path}")
    print(f"{'='*80}")
    print(f"\n💡 Check the output video to verify:")
    print(f"   ✅ Face ALWAYS in frame (even when moving)?")
    print(f"   ✅ Smooth tracking (no jitter)?")
    print(f"   ✅ Handles profile views?")
    
else:
    print(f"\n{'='*80}")
    print(f"⚠️  No detection - will use center crop")
    print(f"{'='*80}")
