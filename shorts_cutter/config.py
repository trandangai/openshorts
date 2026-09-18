"""
Configuration and data models for shorts_cutter.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import os


class ReframingMode(str, Enum):
    PILLAR_BLUR = "pillar_blur"          # 16:9 centered, blurred background fill (fastest, no crop error)
    SMART_CROP = "smart_crop"            # Dynamic/face centered crop to 9:16
    SPLIT_STACK = "split_stack"          # Upper & lower stack for reaction/screen + face


@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float
    probability: float = 1.0

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "probability": round(self.probability, 3),
        }


@dataclass
class Segment:
    id: int
    start: float
    end: float
    text: str
    words: List[WordTimestamp] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
            "words": [w.to_dict() for w in self.words],
        }


@dataclass
class Transcript:
    full_text: str
    language: str
    duration: float
    segments: List[Segment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "full_text": self.full_text,
            "language": self.language,
            "duration": round(self.duration, 3),
            "segments": [s.to_dict() for s in self.segments],
        }


@dataclass
class ViralMoment:
    id: int
    start: float
    end: float
    duration: float
    title: str
    hook: str
    virality_score: int
    reason: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "duration": round(self.duration, 2),
            "title": self.title,
            "hook": self.hook,
            "virality_score": self.virality_score,
            "reason": self.reason,
        }


@dataclass
class JobConfig:
    source_input: str
    job_id: Optional[str] = None
    output_dir: str = "./output/shorts_cutter"
    max_clips: int = 3
    min_clip_duration: float = 15.0
    max_clip_duration: float = 60.0
    whisper_model_size: str = "base"
    gemini_api_key: Optional[str] = None
    gemini_model: str = os.environ.get("GEMINI_MODEL") or "gemini-3.1-flash"
    reframing_mode: ReframingMode = ReframingMode.PILLAR_BLUR
    target_width: int = 1080
    target_height: int = 1920
    burn_subtitles: bool = True
    subtitles_font_size: int = 24
    subtitles_highlight_color: str = "&H00D6FF"  # Yellow BGR (&H00D6FF)
    coverage_mode: str = "part"  # "part" (highlights) or "full" (sequential full video series)
    language: Optional[str] = None  # None / "auto" = auto-detect, or ISO-639-1 code (e.g. "en", "es", "vi", "fr")
    translate_to_english: bool = False  # True = translate foreign audio to English subtitles & voiceover
    kids_storytelling_mode: bool = False  # True = adapt transcript into rhythmic kids storytelling script (±5 words rule)
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None  # None = keep original audio, or specify voice_id to dub/voiceover

    def __post_init__(self):
        if not self.gemini_api_key:
            self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.elevenlabs_api_key:
            self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")
