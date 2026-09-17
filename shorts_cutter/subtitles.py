"""
Subtitle generator for shorts_cutter.
Generates dynamic, viral ASS (Advanced SubStation Alpha) and SRT subtitles
with active-word karaoke highlights for vertical Shorts.
"""

import os
from typing import List, Optional
from shorts_cutter.config import Transcript, WordTimestamp, Segment


def _format_ass_timestamp(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cc"""
    secs = max(0.0, seconds)
    hrs = int(secs // 3600)
    mins = int((secs % 3600) // 60)
    remaining_secs = secs % 60
    centis = int(round((remaining_secs - int(remaining_secs)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{int(remaining_secs):02d}.{centis:02d}"


def _format_srt_timestamp(seconds: float) -> str:
    """Format seconds into SRT timestamp: HH:MM:SS,mmm"""
    secs = max(0.0, seconds)
    hrs = int(secs // 3600)
    mins = int((secs % 3600) // 60)
    remaining_secs = secs % 60
    millis = int(round((remaining_secs - int(remaining_secs)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{int(remaining_secs):02d},{millis:03d}"


def extract_clip_words(
    transcript: Transcript,
    clip_start: float,
    clip_end: float,
) -> List[WordTimestamp]:
    """
    Extract all words within [clip_start, clip_end], offsetting timestamps
    so clip_start becomes 0.0s.
    """
    clip_words = []
    for seg in transcript.segments:
        if seg.end < clip_start or seg.start > clip_end:
            continue
        for w in seg.words:
            if w.end <= clip_start or w.start >= clip_end:
                continue
            # Rebase to 0.0s
            rel_start = max(0.0, w.start - clip_start)
            rel_end = max(rel_start + 0.1, min(clip_end - clip_start, w.end - clip_start))
            clip_words.append(
                WordTimestamp(
                    word=w.word.strip(),
                    start=rel_start,
                    end=rel_end,
                    probability=w.probability,
                )
            )
    return clip_words


def generate_ass_subtitles(
    words: List[WordTimestamp],
    output_ass_path: str,
    font_name: str = "Arial",
    font_size: int = 24,
    primary_color: str = "&H00FFFFFF",      # White in BGR
    highlight_color: str = "&H0000D4FF",    # Bright Yellow/Gold in BGR (&HAABBGGRR)
    outline_color: str = "&H00000000",      # Black outline
    words_per_group: int = 3,
) -> str:
    """
    Generate styled ASS file with dynamic word highlighting (karaoke style).
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size * 2},{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,1,0,1,6,2,2,60,60,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    if not words:
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(header)
        return output_ass_path

    # Group words into small chunks (e.g. 2-4 words) for punchy TikTok readability
    groups = []
    for i in range(0, len(words), words_per_group):
        groups.append(words[i : i + words_per_group])

    for grp in groups:
        grp_start = grp[0].start
        grp_end = grp[-1].end

        # For each word in the group, create an event where that word is highlighted
        for target_idx, active_word in enumerate(grp):
            word_start = active_word.start
            word_end = active_word.end

            # Build line text where active word has highlight_color
            tokens = []
            for j, w in enumerate(grp):
                cleaned_text = w.word.upper()
                if j == target_idx:
                    # Highlighted active word
                    tokens.append(f"{{\\c{highlight_color}&}}{cleaned_text}{{\\c{primary_color}&}}")
                else:
                    tokens.append(cleaned_text)

            line_text = " ".join(tokens)
            ass_start = _format_ass_timestamp(word_start)
            ass_end = _format_ass_timestamp(word_end)
            events.append(
                f"Dialogue: 0,{ass_start},{ass_end},Default,,0,0,0,,{line_text}"
            )

    content = header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_ass_path


def generate_srt_subtitles(
    words: List[WordTimestamp],
    output_srt_path: str,
    words_per_group: int = 4,
) -> str:
    """Generate standard SRT subtitle file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_srt_path)), exist_ok=True)
    if not words:
        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write("")
        return output_srt_path

    groups = [words[i : i + words_per_group] for i in range(0, len(words), words_per_group)]
    lines = []

    for idx, grp in enumerate(groups, start=1):
        start_ts = _format_srt_timestamp(grp[0].start)
        end_ts = _format_srt_timestamp(grp[-1].end)
        text = " ".join(w.word for w in grp)
        lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_srt_path
