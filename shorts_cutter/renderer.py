"""
Rendering module for shorts_cutter.
Assembles, crops/reframes, normalizes audio, burns subtitles, and renders
the final vertical (1080x1920) Short using FFmpeg.
"""

import os
import subprocess
from typing import Optional
from shorts_cutter.config import ViralMoment, ReframingMode
from shorts_cutter.reframer import build_reframing_filter, detect_face_center_x


def _escape_filter_path(path: str) -> str:
    """Escape file path for FFmpeg filtergraph syntax."""
    escaped = os.path.abspath(path).replace("\\", "/")
    escaped = escaped.replace(":", "\\:").replace("'", "\\'")
    return escaped


def render_clip(
    source_video: str,
    moment: ViralMoment,
    output_mp4_path: str,
    subtitles_ass_path: Optional[str] = None,
    audio_override_path: Optional[str] = None,
    reframing_mode: ReframingMode = ReframingMode.PILLAR_BLUR,
    target_width: int = 1080,
    target_height: int = 1920,
    crf: int = 20,
    preset: str = "fast",
) -> str:
    """
    Renders a single vertical Short from source video.
    Optionally replaces original audio with audio_override_path (e.g. ElevenLabs voiceover).
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4_path)), exist_ok=True)

    # Detect face center if smart crop is chosen
    crop_center_x = None
    if reframing_mode == ReframingMode.SMART_CROP:
        print(f"[shorts_cutter:renderer] Analyzing face positions for smart cropping...")
        crop_center_x = detect_face_center_x(
            source_video, start_time=moment.start, sample_duration=min(5.0, moment.duration)
        )
        if crop_center_x is not None:
            print(f"[shorts_cutter:renderer] Detected subject center at x={crop_center_x:.2f}")

    # Build base reframing filter
    reframer_filter = build_reframing_filter(
        mode=reframing_mode,
        src_width=1920,
        src_height=1080,
        target_width=target_width,
        target_height=target_height,
        crop_center_x=crop_center_x,
    )

    # If subtitles provided, chain them to the video stream
    if subtitles_ass_path and os.path.exists(subtitles_ass_path) and os.path.getsize(subtitles_ass_path) > 0:
        escaped_ass = _escape_filter_path(subtitles_ass_path)
        # Note: If reframer ends with [outv], chain ass filter
        if "[outv]" in reframer_filter:
            full_filter = f"{reframer_filter};[outv]ass='{escaped_ass}'[finalv]"
        else:
            full_filter = f"{reframer_filter},ass='{escaped_ass}'[finalv]"
        map_video = "[finalv]"
    else:
        full_filter = reframer_filter
        map_video = "[outv]" if "[outv]" in reframer_filter else "0:v"

    has_audio_override = bool(
        audio_override_path
        and os.path.exists(audio_override_path)
        and os.path.getsize(audio_override_path) > 0
    )

    # Assemble FFmpeg command
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{moment.start:.3f}",
        "-t", f"{moment.duration:.3f}",
        "-i", source_video,
    ]
    if has_audio_override:
        cmd.extend(["-i", audio_override_path])

    cmd.extend([
        "-filter_complex", full_filter,
        "-map", map_video,
        "-map", "1:a:0" if has_audio_override else "0:a?",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-shortest",
        "-movflags", "+faststart",
        output_mp4_path,
    ])

    print(f"[shorts_cutter:renderer] Rendering Short #{moment.id}: '{moment.title}' ({moment.duration:.1f}s)...")
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0 or not os.path.exists(output_mp4_path) or os.path.getsize(output_mp4_path) == 0:
        print(f"[shorts_cutter:renderer] FFmpeg Error: {res.stderr[:600]}")
        raise RuntimeError(f"FFmpeg rendering failed for clip {moment.id}: {res.stderr}")

    size_mb = os.path.getsize(output_mp4_path) / (1024 * 1024)
    print(f"[shorts_cutter:renderer] ✅ Rendered: {output_mp4_path} ({size_mb:.2f} MB)")
    return output_mp4_path
