"""
Transcription module for shorts_cutter.
Extracts audio with FFmpeg and runs faster-whisper locally for word-level timestamps.
Zero external API costs.
"""

import os
import json
import subprocess
from typing import Optional
from shorts_cutter.config import Transcript, Segment, WordTimestamp


def extract_audio(video_path: str, output_wav_path: str) -> str:
    """
    Extract 16kHz mono PCM 16-bit WAV audio from video using FFmpeg.
    """
    if os.path.exists(output_wav_path) and os.path.getsize(output_wav_path) > 1024:
        return output_wav_path

    os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_wav_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(output_wav_path):
        raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")

    return output_wav_path


def transcribe_video(
    video_path: str,
    job_dir: str,
    model_size: str = "base",
    language: Optional[str] = None,
    task: str = "transcribe",
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
) -> Transcript:
    """
    Transcribe video using faster-whisper.
    Returns Transcript object with word-level timestamps.
    """
    transcript_cache = os.path.join(job_dir, "transcript.json")
    if os.path.exists(transcript_cache) and os.path.getsize(transcript_cache) > 10:
        print(f"[shorts_cutter:transcribe] Loading cached transcript from {transcript_cache}")
        with open(transcript_cache, "r", encoding="utf-8") as f:
            data = json.load(f)
        segments = []
        for s in data.get("segments", []):
            words = [
                WordTimestamp(
                    word=w["word"],
                    start=float(w["start"]),
                    end=float(w["end"]),
                    probability=float(w.get("probability", 1.0)),
                )
                for w in s.get("words", [])
            ]
            segments.append(
                Segment(
                    id=int(s["id"]),
                    start=float(s["start"]),
                    end=float(s["end"]),
                    text=s["text"],
                    words=words,
                )
            )
        return Transcript(
            full_text=data.get("full_text", ""),
            language=data.get("language", "en"),
            duration=float(data.get("duration", 0.0)),
            segments=segments,
        )

    # 1. Extract audio
    wav_path = os.path.join(job_dir, "audio.wav")
    print(f"[shorts_cutter:transcribe] Extracting audio to {wav_path}...")
    extract_audio(video_path, wav_path)

    # 2. Determine device & compute type
    import torch
    from faster_whisper import WhisperModel

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"

    print(f"[shorts_cutter:transcribe] Loading faster-whisper model '{model_size}' on {device} ({compute_type})...")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    print(f"[shorts_cutter:transcribe] Transcribing with word timestamps (task={task})...")
    whisper_segments, info = model.transcribe(
        wav_path,
        beam_size=5,
        word_timestamps=True,
        language=language,
        task=task,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    detected_lang = "en" if task == "translate" else info.language
    segments_list = []
    full_text_parts = []
    seg_id = 0

    for seg in whisper_segments:
        words = []
        if seg.words:
            for w in seg.words:
                words.append(
                    WordTimestamp(
                        word=w.word.strip(),
                        start=float(w.start),
                        end=float(w.end),
                        probability=float(w.probability),
                    )
                )
        text = seg.text.strip()
        full_text_parts.append(text)
        segments_list.append(
            Segment(
                id=seg_id,
                start=seg.start,
                end=seg.end,
                text=text,
                words=words,
            )
        )
        seg_id += 1

    duration = segments_list[-1].end if segments_list else 0.0
    transcript = Transcript(
        full_text=" ".join(full_text_parts),
        language=detected_lang,
        duration=duration,
        segments=segments_list,
    )

    # Save cache
    with open(transcript_cache, "w", encoding="utf-8") as f:
        json.dump(transcript.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"[shorts_cutter:transcribe] ✅ Completed: {len(segments_list)} segments, detected language '{detected_lang}'")
    return transcript
