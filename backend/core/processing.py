import os
import ffmpeg
from typing import Optional

def extract_highlight(video_path: str, start_time: str, end_time: str, output_path: str):
    """
    Cuts a segment from the video using FFmpeg.
    start_time and end_time can be in seconds (float) or "HH:MM:SS" format.
    """
    try:
        (
            ffmpeg
            .input(video_path, ss=start_time, to=end_time)
            .output(output_path, c="copy") # Stream copy is faster, but might need re-encoding for reframe
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return output_path
    except ffmpeg.Error as e:
        print(f"FFmpeg Error: {e.stderr.decode('utf-8')}")
        raise

import cv2
import numpy as np

def detect_active_speaker_x(video_path: str, samples: int = 30) -> int:
    """
    Analyzes 'samples' frames from the video to find the MEDIAN X-center of faces.
    Returns the X coordinate (int). Returns None if no faces found.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    if total_frames <= 0: return width // 2
    
    # Load Haar Cascade (built-in to OpenCV)
    # We need to find the data file path. usually in cv2.data.haarcascades
    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    
    centers = []
    
    # Check frames at intervals
    step = max(1, total_frames // samples)
    
    for i in range(0, total_frames, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret: break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # INCREASED minNeighbors to 8 to reduce false positives (e.g. faces on book covers)
        faces = face_cascade.detectMultiScale(gray, 1.1, 8)
        
        # If multiple faces, pick the largest one (assuming active speaker is prominent)
        largest_face = None
        max_area = 0
        
        for (x, y, w, h) in faces:
            area = w * h
            if area > max_area:
                max_area = area
                largest_face = (x, y, w, h)
        
        if largest_face:
            (x, y, w, h) = largest_face
            center_x = x + w // 2
            centers.append(center_x)
            
    cap.release()
    
    if not centers:
        return None
        
    # Return MEDIAN center to avoid outliers (jitter)
    return int(np.median(centers))

# Lazy load YOLO to avoid startup lag
yolo_model = None

def get_color_grading_filter(preset: str) -> str:
    """
    Returns FFmpeg filter string for color grading preset.
    
    Presets:
    - none: No grading (original)
    - cinematic_warm: Warm tones, increased contrast (podcast vibe)
    - cool_modern: Cool blue/teal tones, high contrast (tech feel)
    - vibrant: Boosted saturation, bright (energetic)
    - matte_film: Lifted blacks, faded look (artistic)
    - bw_contrast: Black & white, high contrast (dramatic)
    """
    presets = {
        'none': '',
        # Cinematic Warm: warm tones, higher contrast
        'cinematic_warm': 'eq=contrast=1.15:brightness=0.03:saturation=1.2:gamma=1.1',
        # Cool Modern: blue/teal tones, desaturated
        'cool_modern': 'eq=contrast=1.2:saturation=0.85:gamma_b=0.9:gamma_r=1.1',
        # Vibrant: boosted saturation and contrast
        'vibrant': 'eq=contrast=1.25:saturation=1.4:brightness=0.05:gamma=1.05',
        # Matte Film: lifted blacks (faded look)
        'matte_film': 'eq=contrast=0.85:saturation=0.8:gamma=1.15:brightness=0.05',
        # B&W High Contrast
        'bw_contrast': 'hue=s=0,eq=contrast=1.35:brightness=0.03:gamma=0.95'
    }
    return presets.get(preset, '')

def detect_visual_interest_x(video_path: str, samples: int = 30) -> int:
    """
    Detects the 'Center of Visual Interest' using YOLOv8 AI.
    Prioritizes:
    1. Held Objects (Book, Cell Phone, Laptop, Bottle, Cup, Remote)
    2. Persons (if no objects found)
    """

def detect_faces_mediapipe(video_path: str, width: int, height: int) -> Optional[dict]:
    """
    Detect faces using MediaPipe Face Detection - MUCH more accurate!
    Returns dict with per-frame positions AND face widths for safety margins.
    """
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        import urllib.request
        import os
        
        # Download model if not exists
        model_path = "detector.tflite"
        if not os.path.exists(model_path):
            print("  Downloading MediaPipe face detection model...")
            url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
            urllib.request.urlretrieve(url, model_path)
        
        # Create FaceDetector
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            min_detection_confidence=0.5
        )
        detector = vision.FaceDetector.create_from_options(options)
        
        cap = cv2.VideoCapture(video_path)
        frame_interval = 15
        frame_num = 0
        frame_positions = []
        
        print("  Detecting faces with MediaPipe (accurate bounding boxes)...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_num % frame_interval != 0:
                frame_num += 1
                continue
            
            # Convert to RGB and create MediaPipe Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            
            # Detect faces
            detection_result = detector.detect(mp_image)
            
            if detection_result.detections:
                # Pick best detection
                best_detection = None
                best_score = -1
                
                for detection in detection_result.detections:
                    score = detection.categories[0].score
                    
                    # Get bounding box
                    bbox = detection.bounding_box
                    x = bbox.origin_x
                    y = bbox.origin_y
                    w = bbox.width
                    h = bbox.height
                    
                    # Filter: upper region priority
                    center_y = y + h/2
                    if center_y > height * 0.7:
                        continue
                    
                    # Calculate face center
                    center_x = x + w/2
                    
                    # Score based on size and position
                    area = w * h
                    distance_from_center = abs(center_x - width/2)
                    centrality = 1.0 - (distance_from_center / (width/2))
                    combined_score = (area * 0.7) + (centrality * 1000) + (score * 500)
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_detection = {
                            'center_x': center_x,
                            'face_width': w,
                            'confidence': score,
                            'bbox': (x, y, w, h)
                        }
                
                if best_detection:
                    frame_positions.append((
                        frame_num,
                        best_detection['center_x'],
                        best_detection['face_width'],
                        best_detection['confidence']
                    ))
            
            frame_num += 1
        
        cap.release()
        detector.close()
        
        if len(frame_positions) > 0:
            print(f"  Found {len(frame_positions)} face frames with bounding boxes")
            
            # Calculate average face width
            avg_face_width = sum(w for _, _, w, _ in frame_positions) / len(frame_positions)
            
            return {
                'positions': frame_positions,
                'method': 'mediapipe_face',
                'confidence': sum(c for _, _, _, c in frame_positions) / len(frame_positions),
                'avg_face_width': avg_face_width
            }
        
        print("  No faces detected - will try body tracking")
        return None
        
    except Exception as e:
        print(f"  MediaPipe face detection error: {e}")
        import traceback
        traceback.print_exc()
        return None


def detect_body_positions(video_path: str, width: int, height: int) -> Optional[dict]:
    """
    Detect person body positions using YOLO as fallback when face detection fails.
    Returns dict with per-frame positions for profile views.
    """
    global yolo_model
    try:
        if yolo_model is None:
            from ultralytics import YOLO
            yolo_model = YOLO('yolov8n.pt')
        
        cap = cv2.VideoCapture(video_path)
        frame_interval = 15
        frame_num = 0
        frame_positions = []
        
        print("  Detecting body positions (profile view fallback)...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_num % frame_interval != 0:
                frame_num += 1
                continue
            
            # Run YOLO detection
            results = yolo_model(frame, verbose=False)
            
            best_score = -1
            best_center = None
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    if cls != 0:  # Only persons
                        continue
                    
                    coords = box.xyxy[0].tolist()
                    x1, y1, x2, y2 = coords
                    
                    # Upper region priority
                    center_y = (y1 + y2) / 2
                    if center_y > height * 0.7:
                        continue
                    
                    center_x = (x1 + x2) / 2
                    area = (x2 - x1) * (y2 - y1)
                    
                    # Score: favor larger + more centered
                    distance_from_center = abs(center_x - width/2)
                    centrality_bias = (1.0 - distance_from_center / (width/2)) * area * 0.3
                    score = area + centrality_bias
                    
                    if score > best_score:
                        best_score = score
                        best_center = center_x
            
            if best_center:
                confidence = min(1.0, best_score / 100000)
                # Add placeholder face_width (0) to match MediaPipe format
                frame_positions.append((frame_num, best_center, 0, confidence))
            
            frame_num += 1
        
        cap.release()
        
        if len(frame_positions) > 0:
            print(f"  Found {len(frame_positions)} body frames")
            # No avg_face_width for body tracking
            return {
                'positions': frame_positions,
                'method': 'body',
                'confidence': sum(c for _, _, _, c in frame_positions) / len(frame_positions),
                'avg_face_width': 0  # Placeholder
            }
        
        return None
        
    except Exception as e:
        print(f"  Body tracking error: {e}")
        return None



def create_smooth_trajectory(positions: list, total_frames: int, fps: float) -> dict:
    """
    Create smooth position trajectory for entire video with interpolation.
    Returns dict: {frame_num: x_position} for ALL frames.
    """
    import numpy as np
    from scipy import interpolate
    
    if not positions or len(positions) == 0:
        return None
    
    # Extract frame numbers, positions, and confidence
    # Now positions is (frame_num, x, face_width, confidence)
    frames = [f for f, _, _, _ in positions]
    x_positions = [x for _, x, _, _ in positions]
    face_widths = [w for _, _, w, _ in positions]
    confidences = [c for _, _, _, c in positions]
    
    # Create interpolation function (cubic spline for smooth curves)
    try:
        # Use weighted average for overlapping frames
        unique_frames = []
        unique_positions = []
        
        frame_positions = {}
        for f, x, w, c in positions:
            if f not in frame_positions:
                frame_positions[f] = []
            frame_positions[f].append((x, c))
        
       # Average positions for each frame (weighted by confidence)
        for f in sorted(frame_positions.keys()):
            pos_conf = frame_positions[f]
            total_conf = sum(c for _, c in pos_conf)
            if total_conf > 0:
                avg_x = sum(x * c for x, c in pos_conf) / total_conf
                unique_frames.append(f)
                unique_positions.append(avg_x)
        
        # Interpolate for all frames
        if len(unique_frames) < 2:
            # Not enough data, use single position
            single_pos = int(unique_positions[0])
            return {i: single_pos for i in range(total_frames)}
        
        # Cubic interpolation for smooth motion
        f_interp = interpolate.interp1d(
            unique_frames, unique_positions,
            kind='cubic' if len(unique_frames) >= 4 else 'linear',
            bounds_error=False,
            fill_value=(unique_positions[0], unique_positions[-1])
        )
        
        # Generate position for every frame
        all_frames = np.arange(total_frames)
        interpolated = f_interp(all_frames)
        
        # Apply heavy temporal smoothing to prevent jitter
        window = min(45, int(fps * 1.5))  # ~1.5 seconds of smoothing
        if window > 3:
            kernel = np.hamming(window)
            kernel = kernel / kernel.sum()
            smoothed = np.convolve(interpolated, kernel, mode='same')
        else:
            smoothed = interpolated
        
        # Convert to dict
        trajectory = {i: int(smoothed[i]) for i in range(total_frames)}
        
        print(f"  Created smooth trajectory: {len(trajectory)} frames, window={window}")
        return trajectory
        
    except Exception as e:
        print(f"  Trajectory creation error: {e}, using fallback")
        # Fallback: use median position
        median_pos = int(np.median(x_positions))
        return {i: median_pos for i in range(total_frames)}


def detect_visual_interest_x(video_path: str) -> Optional[dict]:
    """
    FULL DYNAMIC DETECTION - returns per-frame position trajectory.
    
    Returns: {'trajectory': {frame_num: x_pos}, 'fps': fps, 'total_frames': n}
    """
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    
    print(f"Analyzing video: {width}x{height}, {total_frames} frames @ {fps:.2f}fps")
    
    # STAGE 1: MediaPipe Face Detection (accurate bounding boxes)
    print("Stage 1: MediaPipe face detection...")
    detection_data = detect_faces_mediapipe(video_path, width, height)
    
    # STAGE 2: Body Tracking Fallback
    if not detection_data or detection_data['confidence'] < 0.3:
        print("Stage 2: Body tracking (low face confidence)...")
        detection_data = detect_body_positions(video_path, width, height)
    
    if not detection_data:
        print("No detections - using center crop")
        center_x = width // 2
        return {
            'trajectory': {i: center_x for i in range(total_frames)},
            'fps': fps,
            'total_frames': total_frames,
            'width': width,
            'height': height
        }
    
    # Create smooth trajectory for ALL frames
    positions = detection_data['positions']
    trajectory = create_smooth_trajectory(positions, total_frames, fps)
    
    if trajectory is None:
        print("Trajectory creation failed - using median")
        median_x = int(np.median([x for _, x, _, _ in positions]))
        trajectory = {i: median_x for i in range(total_frames)}
    
    # NOTE: Anti-center bias REMOVED - it was causing faces to be shifted off-center
    # Now using raw detected face positions for accurate centering
    
    # Clamp trajectory to valid bounds (prevent out-of-bounds crop)
    target_width = int(height * (9/16))
    for f in trajectory:
        # Ensure crop center is at least target_width/2 from edges
        min_x = target_width // 2
        max_x = width - (target_width // 2)
        trajectory[f] = max(min_x, min(trajectory[f], max_x))
    
    method = detection_data['method']
    confidence = detection_data['confidence']
    avg_face_width = detection_data.get('avg_face_width', 0)
    print(f"Trajectory created: {len(trajectory)} frames (method={method}, conf={confidence:.2f}, avg_face_width={avg_face_width:.0f})")
    
    return {
        'trajectory': trajectory,
        'fps': fps,
        'total_frames': total_frames,
        'width': width,
        'height': height,
        'method': method,
        'confidence': confidence,
        'avg_face_width': avg_face_width
    }


def auto_reframe(video_path: str, output_path: str, color_grading: str = 'none'):
    """
    Reframes video to 9:16 using STATIC CENTERED FACE CROP.
    Applies color grading preset for professional look.
    """
    try:
        # Get video info
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        fps = float(video_stream['r_frame_rate'].split('/')[0]) / float(video_stream['r_frame_rate'].split('/')[1])
        
        # Target 9:16 dimensions
        target_width = int(height * (9/16))
        target_height = height
        
        # STATIC CENTERED FACE CROP (no dynamic movement)
        print("Detecting face for centered stable crop...")
        tracking_data = detect_visual_interest_x(video_path)
        
        if not tracking_data or 'trajectory' not in tracking_data:
            print("Face detection failed - using center crop")
            x = (width - target_width) // 2
            y = 0
        else:
            trajectory = tracking_data['trajectory']
            avg_face_width = tracking_data.get('avg_face_width', 0)
            
            # Calculate WEIGHTED AVERAGE position (weighted by confidence for accuracy)
            # This gives more weight to high-confidence detections
            all_positions = list(trajectory.values())
            
            # Use weighted median - middle 60% of positions (ignore outliers)
            sorted_positions = sorted(all_positions)
            trim_count = int(len(sorted_positions) * 0.2)  # Trim 20% from each end
            if trim_count > 0 and len(sorted_positions) > trim_count * 2:
                trimmed = sorted_positions[trim_count:-trim_count]
            else:
                trimmed = sorted_positions
            
            # Use mean of trimmed positions for smoother centering
            face_center_x = int(sum(trimmed) / len(trimmed))
            
            print(f"Face detected at weighted center X={face_center_x} (from {len(trimmed)} samples)")
            print(f"  Video dimensions: {width}x{height}, target crop: {target_width}x{target_height}")
            print(f"  Face avg width: {avg_face_width:.0f}px")
            
            # CRITICAL: Safety Margin - ensure crop wide enough for FULL HEAD (not just face)
            # MediaPipe face detection only covers face (eyes to chin), not full head
            # Use 2.5x multiplier to include ears, side of head, and some padding
            if avg_face_width > 0:
                required_width = int(avg_face_width * 2.5)  # 2.5x for full head + padding
                print(f"  Required width for full head: {required_width}px (2.5x face width)")
                if required_width > target_width:
                    print(f"  ⚠ Adjusting crop width: {target_width} → {required_width}px for full head visibility")
                    target_width = min(required_width, width)
            
            # Calculate crop X to CENTER the face EXACTLY in the crop
            # Face center should be at crop_x + (crop_width / 2)
            # So: crop_x = face_center - (crop_width / 2)
            half_crop = target_width // 2
            x = face_center_x - half_crop
            
            # SMART CLAMPING: if face is near edge, prioritize keeping face centered
            # even if it means showing some edge
            min_x = 0
            max_x = width - target_width
            
            if x < min_x:
                # Face is too close to left edge
                # Check how far the face would be from center if we clamp
                clamped_face_pos_in_crop = face_center_x - min_x
                offset_from_center = abs(clamped_face_pos_in_crop - half_crop)
                print(f"  Face near left edge: would be {offset_from_center}px off-center")
                x = min_x
            elif x > max_x:
                # Face is too close to right edge
                clamped_face_pos_in_crop = face_center_x - max_x
                offset_from_center = abs(clamped_face_pos_in_crop - half_crop)
                print(f"  Face near right edge: would be {offset_from_center}px off-center")
                x = max_x
            
            y = 0
            
            # Verify centering
            actual_face_in_crop = face_center_x - x
            offset = actual_face_in_crop - half_crop
            print(f"STATIC crop: X={x}, face at {face_center_x}, in-crop position: {actual_face_in_crop}/{target_width} (offset: {offset:+d}px)")
        
        # Apply STATIC crop (single position for entire video - NO SHIFTING!)
        input_stream = ffmpeg.input(video_path)
        audio = input_stream.audio
        video = input_stream.video.filter('crop', target_width, target_height, x, y)
        
        # Apply color grading if specified
        grading_filter = get_color_grading_filter(color_grading)
        if grading_filter:
            print(f"Applying color grading: {color_grading}")
            # Apply each filter in the chain
            for filter_str in grading_filter.split(','):
                filter_str = filter_str.strip()
                if not filter_str:
                    continue
                
                # Parse filter: "eq=contrast=1.1:brightness=0.02" -> filter('eq', contrast=1.1, brightness=0.02)
                if '=' in filter_str:
                    parts = filter_str.split('=', 1)
                    filter_name = parts[0]
                    
                    # Parse parameters
                    params = {}
                    if len(parts) > 1 and parts[1]:
                        param_str = parts[1]
                        for param in param_str.split(':'):
                            if '=' in param:
                                key, value = param.split('=', 1)
                                # Convert to float if numeric
                                try:
                                    params[key] = float(value)
                                except ValueError:
                                    params[key] = value
                    
                    video = video.filter(filter_name, **params)
                else:
                    # Simple filter without parameters
                    video = video.filter(filter_str)
        
        # High-quality encoding
        (
            ffmpeg
            .output(
                video, audio, output_path,
                vcodec='libx264',
                acodec='aac',
                **{
                    'crf': 18,
                    'preset': 'slow',
                    'profile:v': 'high',
                    'b:a': '192k'
                }
            )
            .overwrite_output()
            .run(quiet=False)
        )
        
        print(f"Reframing complete: {output_path}")
    except Exception as e:
        print(f"Reframing error: {e}")
        raise
