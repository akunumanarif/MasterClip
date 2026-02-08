"""
Debug specific frame at 00:15 to see what's being detected
"""
import cv2
import sys
sys.path.append('.')

from core.processing import detect_faces_opencv
import numpy as np

# The clip is 38 seconds, at 00:15 = frame ~450 (at 30fps)
video_path = "temp/test_clip_00_02_19_to_00_02_57.mp4"

cap = cv2.VideoCapture(video_path)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)

print("=" * 80)
print("DEBUG: Frame at 00:15")
print("=" * 80)
print(f"Video: {width}x{height} @ {fps:.2f} fps")

# Jump to frame at 15 seconds
target_frame_num = int(15 * fps)
cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_num)

ret, frame = cap.read()
if ret:
    # Save frame for inspection
    cv2.imwrite("output/debug_frame_00_15.jpg", frame)
    print(f"\n✅ Extracted frame {target_frame_num} → output/debug_frame_00_15.jpg")
    
    # Use Haar Cascade to detect faces
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    
    print(f"\n📊 Face Detection Results:")
    print(f"   Total faces found: {len(faces)}")
    
    if len(faces) > 0:
        print(f"\n   Face Positions:")
        for i, (x, y, w, h) in enumerate(faces):
            center_x = x + w/2
            center_y = y + h/2
            area = w * h
            
            # Check if in upper region
            in_upper = "✅" if center_y < height * 0.7 else "❌ (lower)"
            
            # Centrality
            distance_from_center = abs(center_x - width/2)
            centrality = (1.0 - distance_from_center / (width/2)) * 100
            
            print(f"   Face {i+1}: X={center_x:.0f}, Y={center_y:.0f}, Area={area:.0f}")
            print(f"           Upper region: {in_upper}")
            print(f"           Centrality: {centrality:.1f}%")
            print(f"           Distance from center: {distance_from_center:.0f}px")
            
            # Draw on frame
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Face {i+1}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Mark center line
        cv2.line(frame, (width//2, 0), (width//2, height), (0, 0, 255), 2)
        cv2.putText(frame, "CENTER", (width//2 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Save annotated frame
        cv2.imwrite("output/debug_frame_00_15_annotated.jpg", frame)
        print(f"\n✅ Annotated frame saved → output/debug_frame_00_15_annotated.jpg")
        
        # Now show what clustering would pick
        print(f"\n🎯 Clustering Analysis:")
        
        face_centers = []
        for (x, y, w, h) in faces:
            center_x = x + w/2
            center_y = y + h/2
            
            if center_y < height * 0.7:  # Filter upper region
                face_area = w * h
                distance_from_center = abs(center_x - width/2)
                centrality_score = 1.0 - (distance_from_center / (width/2))
                score = face_area + (centrality_score * 5000)
                
                face_centers.append((center_x, score))
        
        if face_centers:
            face_centers_sorted = sorted(face_centers, key=lambda x: x[1], reverse=True)
            centers_only = [c[0] for c in face_centers_sorted]
            
            # Clustering
            from collections import Counter
            clustered = [round(x / 50) * 50 for x in centers_only]
            position_counts = Counter(clustered)
            
            print(f"   All centers: {[f'{c:.0f}' for c in centers_only]}")
            print(f"   Clustered (50px): {clustered}")
            print(f"   Cluster counts: {dict(position_counts)}")
            
            best_position = position_counts.most_common(1)[0][0]
            print(f"   ✅ Selected position: X={best_position}")
            print(f"   Distance from center: {abs(best_position - width/2):.0f}px")
            
            if abs(best_position - width/2) < 100:
                print(f"   ⚠️  WARNING: Selected position is TOO CLOSE to center!")
                print(f"      This might result in framing empty space!")
        else:
            print(f"   ❌ No faces in upper region - will fallback to YOLO or center")
    else:
        print(f"   ❌ No faces detected - will use fallback")
        
cap.release()

print("\n" + "=" * 80)
print("💡 Open the annotated image to see what was detected")
print("=" * 80)
