"""
Debug script to visualize face detection and center point
"""
import sys
sys.path.append('.')

from core.processing import detect_visual_interest_x
import cv2
import numpy as np

video_path = "temp/test_clip_00_02_19_to_00_02_57.mp4"

print("Analyzing face detection...")
tracking_data = detect_visual_interest_x(video_path)

if tracking_data:
    trajectory = tracking_data['trajectory']
    width = tracking_data['width']
    height = tracking_data['height']
    avg_face_width = tracking_data.get('avg_face_width', 0)
    
    all_positions = list(trajectory.values())
    median_x = int(np.median(all_positions))
    min_x = min(all_positions)
    max_x = max(all_positions)
    
    print(f"\n=== Face Detection Results ===")
    print(f"Video: {width}x{height}")
    print(f"Face width (avg): {avg_face_width:.0f}px")
    print(f"Position range: {min_x} to {max_x} (movement: {max_x-min_x}px)")
    print(f"Median position: {median_x}")
    print(f"Video center: {width//2}")
    print(f"Offset from center: {median_x - width//2} px")
    
    # Calculate current crop
    target_width = int(height * (9/16))
    required_width = int(avg_face_width * 1.5) if avg_face_width > 0 else target_width
    if required_width > target_width:
        target_width = min(required_width, width)
    
    crop_x = median_x - (target_width // 2)
    crop_x = max(0, min(crop_x, width - target_width))
    
    print(f"\n=== Crop Calculation ===")
    print(f"Target crop width: {target_width}px")
    print(f"Crop X: {crop_x}")
    print(f"Crop range: {crop_x} to {crop_x + target_width}")
    print(f"Face center in crop: {median_x - crop_x} (should be {target_width//2} for perfect center)")
    
    # Check if face is centered within crop
    face_pos_in_crop = median_x - crop_x
    crop_center = target_width // 2
    offset = face_pos_in_crop - crop_center
    
    print(f"\n=== Centering Analysis ===")
    print(f"Face position in crop: {face_pos_in_crop}px")
    print(f"Crop center: {crop_center}px")
    print(f"Offset: {offset}px ({'RIGHT' if offset > 0 else 'LEFT'} of center)")
    
    if abs(offset) > 10:
        print(f"\n⚠️  Face NOT centered! Off by {abs(offset)}px")
        print(f"To fix: shift crop by {-offset}px")
    else:
        print(f"\n✅ Face is centered!")
