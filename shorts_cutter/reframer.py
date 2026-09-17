"""
Vertical reframing engine for shorts_cutter.
Converts landscape (16:9) video to vertical (9:16, 1080x1920) for Shorts, TikTok, and Reels.
Supports both stylish Pillar Blur (no information loss) and Smart Speaker Crop.
"""

import os
import subprocess
from typing import Optional, Tuple
from shorts_cutter.config import ReframingMode


def detect_face_center_x(
    video_path: str,
    start_time: float = 0.0,
    sample_duration: float = 5.0,
) -> Optional[float]:
    """
    Detect the average horizontal position (0.0 to 1.0) of the main subject/face
    using OpenCV to optimize crop positioning.
    """
    try:
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        # Seek to start_time
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)

        face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if not os.path.exists(face_cascade_path):
            cap.release()
            return None

        face_cascade = cv2.CascadeClassifier(face_cascade_path)
        frames_to_sample = int(fps * min(sample_duration, 10.0))
        step = max(1, int(fps / 2))  # Sample every ~0.5s

        centers = []
        frame_idx = 0

        while frame_idx < frames_to_sample:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % step == 0:
                h, w = frame.shape[:2]
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60)
                )
                if len(faces) > 0:
                    # Take largest face
                    largest = max(faces, key=lambda f: f[2] * f[3])
                    fx, fy, fw, fh = largest
                    center_norm = (fx + fw / 2.0) / float(w)
                    centers.append(center_norm)

            frame_idx += 1

        cap.release()

        if centers:
            # Return median horizontal center
            centers.sort()
            return centers[len(centers) // 2]
        return None

    except Exception as e:
        print(f"[shorts_cutter:reframer] Face detection warning: {e}")
        return None


def build_reframing_filter(
    mode: ReframingMode = ReframingMode.PILLAR_BLUR,
    src_width: int = 1920,
    src_height: int = 1080,
    target_width: int = 1080,
    target_height: int = 1920,
    crop_center_x: Optional[float] = None,
) -> str:
    """
    Construct FFmpeg video filter-complex string for 9:16 vertical rendering.
    """
    if mode == ReframingMode.PILLAR_BLUR:
        # Background: scale to cover 1080x1920, crop excess, heavy boxblur, slight dimming
        # Foreground: scale to width 1080 maintaining aspect ratio, center vertically
        # Overlay foreground on blurred background
        filter_str = (
            f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height},"
            f"boxblur=luma_radius=min(h\\,w)/20:luma_power=2:chroma_radius=min(h\\,w)/20:chroma_power=2,"
            f"eq=brightness=-0.08[bg];"
            f"[0:v]scale={target_width}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
        )
        return filter_str

    elif mode == ReframingMode.SMART_CROP:
        # Calculate 9:16 crop width
        crop_w = int(src_height * (target_width / float(target_height)))
        crop_w = min(crop_w, src_width)

        if crop_center_x is not None:
            # Center around detected face, clamped inside frame
            desired_x = int((crop_center_x * src_width) - (crop_w / 2.0))
            crop_x = max(0, min(desired_x, src_width - crop_w))
        else:
            # Default center
            crop_x = (src_width - crop_w) // 2

        filter_str = (
            f"[0:v]crop={crop_w}:{src_height}:{crop_x}:0,"
            f"scale={target_width}:{target_height}[outv]"
        )
        return filter_str

    else:
        # Fallback: simple fit
        return f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[outv]"
