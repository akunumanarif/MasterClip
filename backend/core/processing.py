import os
import ffmpeg

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

def detect_visual_interest_x(video_path: str, samples: int = 30) -> int:
    """
    Detects the 'Center of Visual Interest' using YOLOv8 AI.
    Prioritizes:
    1. Held Objects (Book, Cell Phone, Laptop, Bottle, Cup, Remote)
    2. Persons (if no objects found)
    """
    global yolo_model
    try:
        from ultralytics import YOLO
        if yolo_model is None:
            print("Loading YOLOv8 Model...")
            yolo_model = YOLO("yolov8n.pt")
    except ImportError:
        print("Ultralytics/YOLO not installed. Falling back to center.")
        return None

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return None
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    if total_frames <= 0: return width // 2
    
    centers = []
    # Priority classes (COCO indices):
    # 39: bottle, 41: cup, 63: laptop, 67: cell phone, 73: book, 76: scissors
    PRIORITY_CLASSES = [39, 41, 63, 67, 73, 76]
    
    step = max(1, total_frames // samples)
    
    detections = [] # List of (priority, center_x, area)
    
    for i in range(0, total_frames, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret: break
        
        # YOLO Prediction
        results = yolo_model(frame, verbose=False)
        
        frame_best_priority = -1
        frame_best_center = -1
        frame_max_area = 0
        
        persons = [] # Keeping for safety, though unused in new logic
        objects = []
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                # xyxy
                coords = box.xyxy[0].tolist()
                x1, y1, x2, y2 = coords
                area = (x2 - x1) * (y2 - y1)
                
                priority = 0
                if cls == 0: # Person
                    priority = 2 # HIGHEST PRIORITY (Face/Person)
                elif cls in PRIORITY_CLASSES: # Object
                    priority = 1 # FALLBACK PRIORITY (Only if no person)
                
                # Selection Logic (Per Frame):
                if priority > frame_best_priority:
                    frame_best_priority = priority
                    frame_best_center = (x1 + x2) // 2
                    frame_max_area = area
                elif priority == frame_best_priority:
                     if area > frame_max_area:
                        frame_max_area = area
                        frame_best_center = (x1 + x2) // 2
        
        if frame_best_priority > 0:
            detections.append((frame_best_priority, frame_best_center))
            
    cap.release()
    
    if not detections:
        return None
    
    # Global Priority Logic
    # If we found valid objects (priority 2), use them.
    # Else use person (priority 1).
    
    priorities = [d[0] for d in detections]
    max_priority = max(priorities)
    final_centers = [d[1] for d in detections if d[0] == max_priority]

    print(f"YOLO Summary: Found Max Priority {max_priority} in {len(final_centers)}/{len(detections)} frames.")
    
    return int(np.median(final_centers))

def auto_reframe(video_path: str, output_path: str):
    """
    Reframes video to 9:16 using AI Smart Crop (YOLO).
    """
    try:
        # Get video info
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        
        # Target 9:16 dimensions
        target_width = int(height * (9/16))
        target_height = height
        
        # Smart AI Detection
        print("Reframing: Analyzing video content with YOLOv8...")
        center_x = detect_visual_interest_x(video_path)
        
        if center_x is not None:
             print(f"Reframing: Visual Interest detected at X={center_x}")
        else:
             print("Reframing: Nothing detected. Defaulting to center.")
             center_x = width // 2
        
        # Calculate Crop X
        x = center_x - (target_width // 2)
        
        # Clamp bounds
        if x < 0: x = 0
        if x + target_width > width: x = width - target_width
            
        y = 0 # Top alignment for full height

        input_stream = ffmpeg.input(video_path)
        audio = input_stream.audio
        
        # Apply crop
        video = input_stream.video.filter('crop', target_width, target_height, x, y)
        
        (
            ffmpeg
            .output(video, audio, output_path)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return output_path
    except ffmpeg.Error as e:
        print(f"FFmpeg Error: {e.stderr.decode('utf-8')}")
        raise
