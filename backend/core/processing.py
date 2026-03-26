import ffmpeg


def extract_highlight(video_path: str, start_time, end_time, output_path: str):
    """
    Cuts a segment from the video using FFmpeg.
    start_time and end_time can be in seconds (float) or "HH:MM:SS" format.
    """
    try:
        (
            ffmpeg
            .input(video_path, ss=start_time, to=end_time)
            .output(output_path, c="copy")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return output_path
    except ffmpeg.Error as e:
        print(f"FFmpeg Error: {e.stderr.decode('utf-8')}")
        raise


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
        'cinematic_warm': 'eq=contrast=1.15:brightness=0.03:saturation=1.2:gamma=1.1',
        'cool_modern': 'eq=contrast=1.2:saturation=0.85:gamma_b=0.9:gamma_r=1.1',
        'vibrant': 'eq=contrast=1.25:saturation=1.4:brightness=0.05:gamma=1.05',
        'matte_film': 'eq=contrast=0.85:saturation=0.8:gamma=1.15:brightness=0.05',
        'bw_contrast': 'hue=s=0,eq=contrast=1.35:brightness=0.03:gamma=0.95'
    }
    return presets.get(preset, '')
