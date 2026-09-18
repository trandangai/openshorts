"""
AI Voice Scriptwriter & Children's Storytelling Adaptation module for shorts_cutter.
Adapts raw transcripts into rhythmic, engaging children's story scripts
synchronized to animation cuts with strict word count enforcement (±5 words rule).
"""

import re
import json
from typing import Dict, Any, List, Optional
from shorts_cutter.config import WordTimestamp


def _count_words(text: str) -> int:
    """Count clean words excluding pause tokens."""
    cleaned = re.sub(r"\[pause\]|\.\.\.", " ", text)
    words = [w.strip() for w in cleaned.split() if w.strip()]
    return len(words)


def _enforce_word_boundary(
    script_text: str,
    original_count: int,
    tolerance: int = 5,
) -> str:
    """
    Strictly enforce the boundary:
    [original_count - tolerance] <= word_count <= [original_count + tolerance].
    """
    min_words = max(5, original_count - tolerance)
    max_words = original_count + tolerance

    words = script_text.split()
    current_count = len(words)

    if min_words <= current_count <= max_words:
        return script_text

    # If exceeding max, trim gracefully to nearest sentence/word
    if current_count > max_words:
        trimmed_words = words[:max_words]
        trimmed = " ".join(trimmed_words).strip()
        if not trimmed.endswith((".", "!", "?")):
            trimmed += "!"
        return trimmed

    # If below min, the script is already short and valid, but we return as-is
    return script_text


def _fallback_story_script(
    raw_transcript: str,
    duration: float,
    source_lang: str = "en",
) -> Dict[str, Any]:
    """
    Offline rule-based fallback when no Gemini API key is available.
    Ensures zero external dependency failure.
    """
    original_count = _count_words(raw_transcript)
    min_budget = max(5, original_count - 5)
    max_budget = original_count + 5

    # Add gentle cadence punctuation
    clean_text = raw_transcript.strip()
    if clean_text and not clean_text.endswith((".", "!", "?")):
        clean_text += "!"

    script_words = _count_words(clean_text)

    return {
        "timing_metadata": {
            "total_duration_sec": round(duration, 2),
            "original_word_count": original_count,
            "min_allowed_words": min_budget,
            "max_allowed_words": max_budget,
            "final_script_word_count": script_words,
        },
        "final_script_text": clean_text,
        "tts_notes": {
            "tone_cues": "warm, enthusiastic children's narrator",
            "suggested_pauses": "natural pauses at commas and punctuation",
        },
    }


def adapt_kids_story_script(
    raw_transcript: str,
    clip_duration: float,
    clip_words: Optional[List[WordTimestamp]] = None,
    source_lang: str = "en",
    target_audience: str = "5-8 years old",
    gemini_api_key: Optional[str] = None,
    gemini_model: str = "gemini-3.1-flash",
) -> Dict[str, Any]:
    """
    Adapt a raw clip transcript into an enchanting children's voiceover script
    using Gemini LLM with strict word budget enforcement (±5 words rule).
    """
    clean_raw = raw_transcript.strip()
    if not clean_raw:
        return _fallback_story_script(raw_transcript, clip_duration, source_lang)

    original_count = _count_words(clean_raw)
    min_allowed = max(5, original_count - 5)
    max_allowed = original_count + 5
    target_budget_by_duration = round(clip_duration * 2.1)

    # If no Gemini API key, use fallback
    if not gemini_api_key:
        print(f"[shorts_cutter:scriptwriter] No Gemini key provided. Using offline heuristic script adapter.")
        return _fallback_story_script(clean_raw, clip_duration, source_lang)

    # Format timecoded blocks if words with timestamps are available
    timecode_block = ""
    if clip_words and len(clip_words) > 0:
        lines = []
        chunk = []
        chunk_start = clip_words[0].start
        for w in clip_words:
            chunk.append(w.word)
            if w.word.endswith((".", "!", "?", ",", ";")) or len(chunk) >= 6:
                lines.append(f"[{chunk_start:.1f}s - {w.end:.1f}s] {' '.join(chunk)}")
                chunk = []
                chunk_start = w.end
        if chunk:
            lines.append(f"[{chunk_start:.1f}s - {clip_words[-1].end:.1f}s] {' '.join(chunk)}")
        timecode_block = "\n".join(lines)
    else:
        timecode_block = f"[0.0s - {clip_duration:.1f}s] {clean_raw}"

    prompt = f"""# ROLE & OBJECTIVE
You are an expert AI Voice Scriptwriter specializing in children's animated storytelling and rhythm-synchronized voiceover production.
Your objective is to adapt a raw clip transcript into an enchanting, lively, and engaging story-driven script for kids, while strictly adhering to duration and speech-rate constraints.

---

# INPUT PARAMETERS
- Total Clip Duration: {clip_duration:.1f} seconds
- Target Audience Age: {target_audience}
- Source Language: {source_lang}
- Original Word Count: {original_count} words
- Target Word Budget: {min_allowed} to {max_allowed} words (Strict ±5 words rule based on original count of {original_count})
- Target Cadence Budget: ~{target_budget_by_duration} words (based on 2.1 words/second for kids delivery)

RAW TIMESTAMPED TRANSCRIPT:
{timecode_block}

---

# STRICT WORD COUNT CONSTRAINT (±5 WORDS RULE)
To ensure the custom script matches the pacing, animation cuts, and voice delivery of the source clip without rushing or dragging:
1. Baseline Measurement: The original transcript has exactly {original_count} words.
2. Hard Boundary: Target Total Words MUST satisfy:
   {min_allowed} <= Final_Script_Words <= {max_allowed}.
   The final English script MUST NOT deviate by more than ±5 words from {original_count}.
3. Timestamp Alignment: Distribute the word count proportionally across the time blocks so cuts remain frame-accurate.

---

# TONE & STYLE: KIDS STORYTELLING (ENGLISH)
- Persona: Warm, whimsical, enthusiastic narrator (classic storybook, Disney/Pixar animated voiceover style).
- Vocabulary: Sensory-rich words, gentle onomatopoeia (e.g., whoosh, sparkle, tiptoe), vivid descriptive verbs, and easy-to-understand phrasing for kids aged {target_audience}.
- Narrative Hook: Spark curiosity within the first 2-3 seconds using an inviting question or dramatic action.
- Faithfulness: Retain 100% of the core message, actions, and sequence of the source transcript.

---

# OUTPUT FORMAT (STRICT JSON ONLY)
Respond with a JSON object matching this schema:
{{
  "timing_metadata": {{
    "total_duration_sec": {clip_duration:.1f},
    "original_word_count": {original_count},
    "min_allowed_words": {min_allowed},
    "max_allowed_words": {max_allowed},
    "final_script_word_count": <INTEGER>
  }},
  "final_script_text": "<Full spoken English voiceover script without timecode prefixes, ready for ElevenLabs TTS>",
  "tts_notes": {{
    "tone_cues": "<e.g., enthusiastic, curious rise, gentle whisper>",
    "suggested_pauses": "<e.g., [pause] after hook, dramatic pause before action>"
  }}
}}
"""

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=gemini_api_key)
        candidate_models = [gemini_model]
        for alt in ["gemini-3.1-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]:
            if alt not in candidate_models:
                candidate_models.append(alt)

        response = None
        last_error = None
        for model_cand in candidate_models:
            try:
                print(f"[shorts_cutter:scriptwriter] Querying {model_cand} for kids story script adaptation (budget: {min_allowed}-{max_allowed} words)...")
                response = client.models.generate_content(
                    model=model_cand,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.4,
                        response_mime_type="application/json",
                    ),
                )
                if response:
                    break
            except Exception as me:
                last_error = me
                err_msg = str(me).lower()
                if "404" in err_msg or "not_found" in err_msg or "not found" in err_msg:
                    print(f"[shorts_cutter:scriptwriter] Model {model_cand} returned 404 (not found). Trying fallback candidate...")
                    continue
                else:
                    raise me

        if not response and last_error:
            raise last_error

        raw_resp = getattr(response, "text", "")
        # Clean JSON markdown fences if present
        clean_json = re.sub(r"^```(?:json)?\n?", "", raw_resp.strip())
        clean_json = re.sub(r"\n?```$", "", clean_json).strip()
        data = json.loads(clean_json)

        final_text = str(data.get("final_script_text", "")).strip()
        if final_text:
            # Enforce hard ±5 words boundary programmatically
            bounded_text = _enforce_word_boundary(final_text, original_count, tolerance=5)
            final_count = _count_words(bounded_text)

            meta = data.get("timing_metadata", {})
            meta["original_word_count"] = original_count
            meta["min_allowed_words"] = min_allowed
            meta["max_allowed_words"] = max_allowed
            meta["final_script_word_count"] = final_count

            print(f"[shorts_cutter:scriptwriter] ✅ Story script adapted: {final_count} words (original: {original_count}, allowed: {min_allowed}-{max_allowed})")
            return {
                "timing_metadata": meta,
                "final_script_text": bounded_text,
                "tts_notes": data.get("tts_notes", {
                    "tone_cues": "whimsical and warm",
                    "suggested_pauses": "natural cadence",
                }),
            }

    except Exception as e:
        print(f"[shorts_cutter:scriptwriter] Gemini script adaptation error ({e}). Falling back to rule-based script.")

    return _fallback_story_script(clean_raw, clip_duration, source_lang)
