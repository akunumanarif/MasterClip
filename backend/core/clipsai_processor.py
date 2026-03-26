import os
import ffmpeg
from clipsai import Transcriber, ClipFinder, resize, MediaEditor
from core.processing import get_color_grading_filter


def auto_detect_clips(video_path: str) -> list:
    """
    Transcribes video with WhisperX and auto-detects clip boundaries using ClipsAI.
    Returns list of (start_time_sec, end_time_sec) tuples.
    """
    print("  Transcribing video with WhisperX...")
    transcriber = Transcriber()
    transcription = transcriber.transcribe(audio_file_path=video_path)

    print("  Finding clips via transcript analysis...")
    clipfinder = ClipFinder()
    clips = clipfinder.find_clips(transcription=transcription)

    result = [(clip.start_time, clip.end_time) for clip in clips]
    print(f"  Found {len(result)} clips automatically")
    return result


def reframe_clip_clipsai(
    video_path: str,
    output_path: str,
    pyannote_token: str,
    color_grading: str = 'none'
):
    """
    Reframes a video clip to 9:16 using ClipsAI speaker-tracking resize.
    Uses Pyannote speaker diarization for accurate face/speaker tracking.
    Applies color grading as a post-process FFmpeg step if specified.
    """
    print(f"  Analyzing speakers with ClipsAI resize (Pyannote)...")
    crops = resize(
        video_file_path=video_path,
        pyannote_auth_token=pyannote_token,
        aspect_ratio=(9, 16)
    )

    grading_filter = get_color_grading_filter(color_grading)

    if grading_filter:
        # Reframe to a temp file first, then apply color grading
        temp_reframed = output_path + "_temp.mp4"
        print(f"  Applying ClipsAI crop...")
        editor = MediaEditor()
        editor.resize_video(
            original_video_file_path=video_path,
            crops=crops,
            resized_video_file_path=temp_reframed
        )

        print(f"  Applying color grading: {color_grading}")
        input_stream = ffmpeg.input(temp_reframed)
        video = input_stream.video

        for f in grading_filter.split(','):
            f = f.strip()
            if not f:
                continue
            if '=' in f:
                name, params_str = f.split('=', 1)
                params = {}
                for p in params_str.split(':'):
                    if '=' in p:
                        k, v = p.split('=', 1)
                        try:
                            params[k] = float(v)
                        except ValueError:
                            params[k] = v
                video = video.filter(name, **params)
            else:
                video = video.filter(f)

        (
            ffmpeg
            .output(
                video, input_stream.audio, output_path,
                vcodec='libx264',
                acodec='aac',
                **{
                    'crf': 18,
                    'preset': 'slow',
                    'profile:v': 'high',
                    'b:a': '192k',
                    'movflags': '+faststart',
                    'pix_fmt': 'yuv420p'
                }
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        os.remove(temp_reframed)
    else:
        print(f"  Applying ClipsAI crop...")
        editor = MediaEditor()
        editor.resize_video(
            original_video_file_path=video_path,
            crops=crops,
            resized_video_file_path=output_path
        )

    print(f"  Reframing complete: {output_path}")
