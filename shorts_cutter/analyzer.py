"""
Viral moment analyzer for shorts_cutter.
Uses Google Gemini Flash (free tier) to identify viral hooks and segments,
with an intelligent rule-based heuristic fallback for 100% offline/zero-API execution.
"""

import re
import json
from typing import List, Optional
from shorts_cutter.config import Transcript, ViralMoment


def _extract_json(text: str) -> Optional[list]:
    """Safely extract JSON array from LLM response text."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None


def _heuristic_analyze_moments(
    transcript: Transcript,
    max_clips: int = 3,
    min_duration: float = 15.0,
    max_duration: float = 60.0,
    coverage_mode: str = "part",
) -> List[ViralMoment]:
    """
    Offline heuristic moment finder:
    - coverage_mode='part': Identifies high-density speech segments bounded by natural pauses.
    - coverage_mode='full': Sequentially partitions the entire video into Part 1, Part 2, ...
    Guarantees the system works even without an API key.
    """
    if not transcript.segments:
        return []

    total_duration = transcript.duration
    segments = transcript.segments

    # --- Full Series Coverage Mode ---
    if coverage_mode == "full":
        parts = []
        win_start = max(0.0, segments[0].start)
        win_segments = []

        for seg in segments:
            win_segments.append(seg)
            cur_dur = seg.end - win_start
            is_sentence_break = seg.text.rstrip().endswith((".", "!", "?", "...", ":", ";"))

            if (cur_dur >= min_duration and is_sentence_break) or cur_dur >= max_duration:
                part_num = len(parts) + 1
                hook_candidate = win_segments[0].text.strip()
                preview = hook_candidate[:50].strip() + ("..." if len(hook_candidate) > 50 else "")
                title = f"Part {part_num}: {preview}" if preview else f"Part {part_num}"

                word_count = sum(len(s.words) for s in win_segments)
                wps = word_count / max(1.0, cur_dur)
                score = int(min(95, max(65, 65 + (wps * 7))))

                parts.append(
                    ViralMoment(
                        id=part_num,
                        start=round(win_start, 2),
                        end=round(seg.end, 2),
                        duration=round(cur_dur, 2),
                        title=title,
                        hook=hook_candidate[:90],
                        virality_score=score,
                        reason=f"Sequential Part {part_num} covering video timeline ({win_start:.1f}s - {seg.end:.1f}s).",
                    )
                )
                win_start = seg.end
                win_segments = []
                if len(parts) >= max_clips:
                    break

        # Handle leftover segments at the end of the video
        if win_segments and len(parts) < max_clips:
            cur_dur = win_segments[-1].end - win_start
            if cur_dur >= min_duration:
                part_num = len(parts) + 1
                hook_candidate = win_segments[0].text.strip()
                preview = hook_candidate[:50].strip() + ("..." if len(hook_candidate) > 50 else "")
                title = f"Part {part_num}: {preview}" if preview else f"Part {part_num}"
                parts.append(
                    ViralMoment(
                        id=part_num,
                        start=round(win_start, 2),
                        end=round(win_segments[-1].end, 2),
                        duration=round(cur_dur, 2),
                        title=title,
                        hook=hook_candidate[:90],
                        virality_score=75,
                        reason=f"Sequential Part {part_num} covering conclusion of the video.",
                    )
                )
            elif parts:
                # If leftover is too short, extend the last part to cover up to the end
                parts[-1].end = round(win_segments[-1].end, 2)
                parts[-1].duration = round(parts[-1].end - parts[-1].start, 2)

        return parts

    # --- Part / Viral Highlights Mode ---
    # If the whole video is short (e.g. <= max_duration), use the whole video or its best slice
    if total_duration <= max_duration:
        start_time = max(0.0, segments[0].start)
        end_time = min(total_duration, segments[-1].end)
        if end_time - start_time >= min_duration:
            hook_text = segments[0].text[:80] + "..." if len(segments[0].text) > 80 else segments[0].text
            return [
                ViralMoment(
                    id=1,
                    start=start_time,
                    end=end_time,
                    duration=round(end_time - start_time, 2),
                    title="Key Highlight",
                    hook=hook_text,
                    virality_score=85,
                    reason="Complete coherent segment fitting short duration.",
                )
            ]

    # Partition segments into candidate windows
    candidates = []
    window_start = segments[0].start
    window_segments = []

    for seg in segments:
        window_segments.append(seg)
        cur_dur = seg.end - window_start

        if cur_dur >= min_duration:
            # Score window based on word count / speech density
            word_count = sum(len(s.words) for s in window_segments)
            wps = word_count / max(1.0, cur_dur)  # words per second
            hook = window_segments[0].text.strip()
            score = int(min(95, max(60, 60 + (wps * 8))))

            candidates.append(
                ViralMoment(
                    id=len(candidates) + 1,
                    start=window_start,
                    end=seg.end,
                    duration=round(cur_dur, 2),
                    title=f"Viral Segment {len(candidates) + 1}",
                    hook=hook[:90],
                    virality_score=score,
                    reason=f"High speech engagement density ({wps:.1f} words/sec).",
                )
            )

            # Move window forward
            if len(candidates) >= max_clips * 2:
                break
            # Advance start to next natural break
            window_segments = []
            window_start = seg.end

    # Sort by virality score and return top max_clips
    candidates.sort(key=lambda m: m.virality_score, reverse=True)
    selected = candidates[:max_clips]
    # Re-index
    for idx, m in enumerate(selected):
        m.id = idx + 1
    return selected


def analyze_viral_moments(
    transcript: Transcript,
    gemini_api_key: Optional[str] = None,
    gemini_model: str = "gemini-2.0-flash",
    max_clips: int = 3,
    min_duration: float = 15.0,
    max_duration: float = 60.0,
    coverage_mode: str = "part",
) -> List[ViralMoment]:
    """
    Find viral clips from transcript using Gemini Flash or heuristic fallback.
    Supports coverage_mode="part" (top viral hooks) or coverage_mode="full" (sequential multi-part series).
    """
    if not transcript.segments:
        print("[shorts_cutter:analyzer] Warning: Empty transcript, no moments found.")
        return []

    # If no Gemini API key, use the local heuristic analyzer
    if not gemini_api_key:
        print(f"[shorts_cutter:analyzer] No Gemini API key provided. Using local heuristic moment analyzer (mode: {coverage_mode}, $0 cost).")
        return _heuristic_analyze_moments(transcript, max_clips, min_duration, max_duration, coverage_mode=coverage_mode)

    # Format transcript with line timestamps for Gemini
    formatted_lines = []
    for s in transcript.segments:
        formatted_lines.append(f"[{s.start:.1f}s - {s.end:.1f}s] {s.text}")
    transcript_block = "\n".join(formatted_lines)

    if coverage_mode == "full":
        prompt = f"""You are an elite short-form video editor for TikTok, YouTube Shorts, and Instagram Reels.
Your task is to partition this ENTIRE video into a continuous, sequential multi-part series of Shorts (Part 1, Part 2, Part 3, etc.) covering the FULL timeline from start to finish without gaps.

REQUIREMENTS:
1. Cover the entire timeline sequentially. Clip 1 starts at 0.0s (or the first spoken word). Clip 2 starts where Clip 1 ends, and so on.
2. Each clip MUST have a duration between {min_duration:.0f} and {max_duration:.0f} seconds (end - start).
3. End each clip at natural sentence boundaries or pauses.
4. Each clip title MUST begin with "Part 1: ", "Part 2: ", etc., followed by a punchy chapter topic (e.g. "Part 1: The Hidden Problem").
5. Extract up to {max_clips} sequential parts covering the video timeline from beginning to end.
6. Timestamps MUST match actual boundaries in the transcript.
7. Return ONLY a valid JSON array of objects with this schema:
[
  {{
    "id": 1,
    "start": 0.0,
    "end": 45.0,
    "title": "Part 1: The Unexpected Discovery",
    "hook": "Opening spoken hook text",
    "virality_score": 90,
    "reason": "Sequential Chapter 1 establishing the core premise"
  }}
]

TRANSCRIPT:
{transcript_block}
"""
    else:
        prompt = f"""You are an elite short-form video editor for TikTok, YouTube Shorts, and Instagram Reels.
Analyze this video transcript with timestamps and find the TOP {max_clips} most viral, engaging, and standalone clips.

REQUIREMENTS:
1. Each clip MUST have a duration between {min_duration:.0f} and {max_duration:.0f} seconds (end - start).
2. Each clip MUST start with a strong HOOK (a provocative statement, surprising insight, or clear problem).
3. Each clip MUST be standalone and make complete sense to a viewer scrolling on TikTok.
4. Timestamps MUST match actual boundaries in the transcript.
5. Return ONLY a valid JSON array of objects with this schema:
[
  {{
    "id": 1,
    "start": 12.5,
    "end": 45.0,
    "title": "Short punchy video title",
    "hook": "Opening spoken hook text",
    "virality_score": 92,
    "reason": "Why this will hook viewers and perform well"
  }}
]

TRANSCRIPT:
{transcript_block}
"""

    try:
        from google import genai
        from google.genai import types

        print(f"[shorts_cutter:analyzer] Querying {gemini_model} for viral moments (mode: {coverage_mode})...")
        client = genai.Client(api_key=gemini_api_key)
        response = client.models.generate_content(
            model=gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )

        data = _extract_json(getattr(response, "text", ""))
        if data and isinstance(data, list):
            moments = []
            for item in data[:max_clips]:
                start = float(item.get("start", 0.0))
                end = float(item.get("end", 0.0))
                dur = end - start
                if dur < 5.0:
                    continue
                moments.append(
                    ViralMoment(
                        id=int(item.get("id", len(moments) + 1)),
                        start=start,
                        end=end,
                        duration=round(dur, 2),
                        title=str(item.get("title", "Viral Clip")),
                        hook=str(item.get("hook", "")),
                        virality_score=int(item.get("virality_score", 85)),
                        reason=str(item.get("reason", "")),
                    )
                )
            if moments:
                print(f"[shorts_cutter:analyzer] ✅ Gemini found {len(moments)} clips (coverage: {coverage_mode})!")
                return moments

    except Exception as e:
        print(f"[shorts_cutter:analyzer] Gemini analysis failed or timed out ({e}). Falling back to local heuristic analyzer.")

    return _heuristic_analyze_moments(transcript, max_clips, min_duration, max_duration, coverage_mode=coverage_mode)
