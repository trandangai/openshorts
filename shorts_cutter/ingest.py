"""
Ingestion module for shorts_cutter.
Handles YouTube video download via yt-dlp and local file validation via ffprobe.
"""

import os
import re
import json
import shutil
import subprocess
from typing import Dict, Any, Optional
from urllib.parse import urlparse


def is_url(source: str) -> bool:
    """Check if the given string is a valid web URL."""
    try:
        res = urlparse(source)
        return res.scheme in ("http", "https") and bool(res.netloc)
    except Exception:
        return False


def probe_video(video_path: str) -> Dict[str, Any]:
    """
    Run ffprobe on a local video file to extract format and stream metadata.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=width,height,r_frame_rate,codec_type,codec_name",
        "-of", "json",
        video_path,
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed on {video_path}: {e.stderr}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"ffprobe output invalid JSON: {e}")

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        raise ValueError(f"No video stream found in {video_path}")

    # Parse frame rate
    fps_raw = video_stream.get("r_frame_rate", "30/1")
    if "/" in fps_raw:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 30.0
    else:
        fps = float(fps_raw)

    duration = float(format_info.get("duration") or 0.0)
    if duration == 0.0:
        # Fallback to stream duration if format duration missing
        duration = float(video_stream.get("duration") or 0.0)

    return {
        "path": os.path.abspath(video_path),
        "duration": duration,
        "width": int(video_stream.get("width") or 1920),
        "height": int(video_stream.get("height") or 1080),
        "fps": round(fps, 2),
        "video_codec": video_stream.get("codec_name", "unknown"),
        "has_audio": audio_stream is not None,
        "size_bytes": int(format_info.get("size") or os.path.getsize(video_path)),
    }


def download_youtube_video(url: str, output_dir: str) -> str:
    """
    Download a video from YouTube (or any supported URL) using yt-dlp.
    Saves to output_dir/source.mp4.
    """
    import yt_dlp

    os.makedirs(output_dir, exist_ok=True)
    target_path = os.path.join(output_dir, "source.mp4")

    # If source.mp4 already downloaded and valid, reuse it
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1024:
        print(f"[shorts_cutter:ingest] Reusing existing downloaded video: {target_path}")
        return target_path

    outtmpl = os.path.join(output_dir, "source.%(ext)s")

    ydl_opts = {
        # Select best mp4 video <= 1080p + best m4a audio, merged to mp4
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": True,
        "noplaylist": True,
        "overwrites": True,
        "socket_timeout": 30,
    }

    print(f"[shorts_cutter:ingest] Downloading YouTube video from {url}...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Find the downloaded file
    if os.path.exists(target_path):
        return target_path

    # Check for any .mp4 or .mkv in output_dir
    candidates = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.startswith("source.") and not f.endswith(".part")
    ]
    if candidates:
        candidate = candidates[0]
        if candidate != target_path:
            shutil.move(candidate, target_path)
        return target_path

    raise FileNotFoundError(f"Download finished but failed to locate source video in {output_dir}")


def ingest_media(source_input: str, job_dir: str) -> Dict[str, Any]:
    """
    Unified entrypoint: ingests either a URL or local file path.
    Returns probed video metadata dictionary.
    """
    os.makedirs(job_dir, exist_ok=True)

    if is_url(source_input):
        video_path = download_youtube_video(source_input, job_dir)
    else:
        # Local file
        if not os.path.exists(source_input):
            raise FileNotFoundError(f"Local video file not found: {source_input}")
        
        # Create a symlink or copy to job_dir/source.mp4 for uniform processing
        target_path = os.path.join(job_dir, "source.mp4")
        if os.path.abspath(source_input) != os.path.abspath(target_path):
            if not os.path.exists(target_path):
                try:
                    os.symlink(os.path.abspath(source_input), target_path)
                except OSError:
                    shutil.copyfile(source_input, target_path)
        video_path = target_path

    meta = probe_video(video_path)
    print(f"[shorts_cutter:ingest] Media ready: {meta['width']}x{meta['height']} @ {meta['fps']}fps, {meta['duration']:.1f}s")
    return meta
