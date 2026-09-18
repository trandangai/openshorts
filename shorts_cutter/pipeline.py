"""
Pipeline orchestrator for shorts_cutter.
Coordinates ingestion, transcription, moment analysis, subtitles, and rendering.
"""

import os
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from shorts_cutter.config import JobConfig, ReframingMode, ViralMoment
from shorts_cutter.ingest import ingest_media, probe_audio_duration
from shorts_cutter.transcriber import transcribe_video
from shorts_cutter.analyzer import analyze_viral_moments
from shorts_cutter.subtitles import (
    extract_clip_words,
    generate_ass_subtitles,
    generate_srt_subtitles,
    rescale_words_to_duration,
)
from shorts_cutter.renderer import render_clip
from shorts_cutter.voiceover import generate_clip_voiceover


def run_pipeline(config: JobConfig, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    Execute full end-to-end shorts cutting pipeline.
    """
    job_id = config.job_id or str(uuid.uuid4())[:8]
    clean_out = config.output_dir.rstrip("/\\")
    if os.path.basename(clean_out) == f"job_{job_id}":
        job_dir = clean_out
    else:
        job_dir = os.path.join(clean_out, f"job_{job_id}")
    os.makedirs(job_dir, exist_ok=True)

    start_time = time.time()
    result = {
        "job_id": job_id,
        "status": "PROCESSING",
        "job_dir": os.path.abspath(job_dir),
        "source_input": config.source_input,
        "clips": [],
        "errors": [],
    }

    def update_progress(stage: str, percent: int, msg: str):
        print(f"[shorts_cutter:pipeline] [{percent}%] {stage}: {msg}")
        if progress_callback:
            progress_callback(stage, percent, msg)

    try:
        # 1. Ingestion
        update_progress("INGEST", 10, "Ingesting video source...")
        media_info = ingest_media(config.source_input, job_dir)
        source_video_path = media_info["path"]
        result["media_info"] = media_info

        # 2. Transcription
        transcribe_lang = config.language if config.language and config.language.lower() != "auto" else None
        transcribe_task = "translate" if config.translate_to_english else "transcribe"
        update_progress("TRANSCRIBE", 30, f"Transcribing audio locally with faster-whisper (lang={transcribe_lang or 'auto'}, task={transcribe_task})...")
        transcript = transcribe_video(
            video_path=source_video_path,
            job_dir=job_dir,
            model_size=config.whisper_model_size,
            language=transcribe_lang,
            task=transcribe_task,
        )
        result["transcript_stats"] = {
            "language": transcript.language,
            "duration": transcript.duration,
            "segments_count": len(transcript.segments),
            "words_count": sum(len(s.words) for s in transcript.segments),
        }

        # 3. Viral Moment Detection
        update_progress("ANALYZE", 50, f"Detecting clips ({config.coverage_mode} coverage)...")
        moments = analyze_viral_moments(
            transcript=transcript,
            gemini_api_key=config.gemini_api_key,
            gemini_model=config.gemini_model,
            max_clips=config.max_clips,
            min_duration=config.min_clip_duration,
            max_duration=config.max_clip_duration,
            coverage_mode=config.coverage_mode,
        )

        # Fallback if no moments found (e.g. silent video or very short)
        if not moments:
            print("[shorts_cutter:pipeline] No moments found from transcript. Using full video fallback.")
            total_dur = min(media_info["duration"], config.max_clip_duration)
            moments = [
                ViralMoment(
                    id=1,
                    start=0.0,
                    end=total_dur,
                    duration=round(total_dur, 2),
                    title="Short Highlight",
                    hook="",
                    virality_score=75,
                    reason="Visual fallback for video segment.",
                )
            ]

        result["moments"] = [m.to_dict() for m in moments]

        # 4. Clip Rendering & Subtitles
        clips_dir = os.path.join(job_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        rendered_clips = []
        total_moments = len(moments)

        for idx, m in enumerate(moments):
            progress_pct = 50 + int(((idx + 1) / total_moments) * 45)
            update_progress("RENDER", progress_pct, f"Rendering Short #{m.id} ({m.duration:.1f}s)...")

            ass_path = None
            srt_path = None
            clip_words = extract_clip_words(transcript, m.start, m.end)
            raw_clip_text = " ".join(w.word for w in clip_words).strip()

            # Optional AI Voice Scriptwriter & Storytelling Adaptation
            story_script_meta = None
            active_script_words = clip_words
            active_clip_text = raw_clip_text

            if config.kids_storytelling_mode and raw_clip_text:
                try:
                    update_progress("SCRIPTWRITER", progress_pct, f"Adapting kids storytelling script for Short #{m.id} (±5 words rule)...")
                    from shorts_cutter.scriptwriter import adapt_kids_story_script
                    from shorts_cutter.subtitles import align_text_to_duration
                    script_data = adapt_kids_story_script(
                        raw_transcript=raw_clip_text,
                        clip_duration=m.duration,
                        clip_words=clip_words,
                        source_lang=transcript.language,
                        gemini_api_key=config.gemini_api_key,
                        gemini_model=config.gemini_model,
                    )
                    story_script_meta = script_data
                    active_clip_text = script_data.get("final_script_text", raw_clip_text)
                    active_script_words = align_text_to_duration(active_clip_text, m.duration)
                except Exception as se:
                    print(f"[shorts_cutter:pipeline] Story script adaptation warning: {se}. Using raw transcript.")

            # Optional ElevenLabs Voiceover / Voice Changing
            audio_override_path = None
            if config.elevenlabs_voice_id and config.elevenlabs_api_key:
                if active_clip_text:
                    try:
                        update_progress("VOICEOVER", progress_pct, f"Synthesizing ElevenLabs voice for Short #{m.id}...")
                        voice_out = os.path.join(clips_dir, f"voiceover_{m.id}.mp3")
                        target_lang = "en" if (config.translate_to_english or config.kids_storytelling_mode) else (config.language if config.language and config.language.lower() != "auto" else transcript.language)
                        generate_clip_voiceover(
                            text=active_clip_text,
                            api_key=config.elevenlabs_api_key,
                            output_path=voice_out,
                            voice_id=config.elevenlabs_voice_id,
                            language_code=target_lang,
                        )
                        audio_override_path = voice_out

                        # Rescale subtitle word timestamps to match ElevenLabs audio duration perfectly
                        voice_duration = probe_audio_duration(voice_out)
                        if voice_duration > 0:
                            active_script_words = rescale_words_to_duration(active_script_words, voice_duration)
                    except Exception as ve:
                        print(f"[shorts_cutter:pipeline] ElevenLabs voiceover warning: {ve}. Falling back to original audio.")
                        audio_override_path = None

            if config.burn_subtitles:
                ass_path = os.path.join(clips_dir, f"clip_{m.id}.ass")
                srt_path = os.path.join(clips_dir, f"clip_{m.id}.srt")
                generate_ass_subtitles(
                    words=active_script_words,
                    output_ass_path=ass_path,
                    font_size=config.subtitles_font_size,
                    highlight_color=config.subtitles_highlight_color,
                    words_per_group=5,
                )
                generate_srt_subtitles(words=active_script_words, output_srt_path=srt_path, words_per_group=5)

            output_mp4 = os.path.join(clips_dir, f"clip_{m.id}.mp4")
            render_clip(
                source_video=source_video_path,
                moment=m,
                output_mp4_path=output_mp4,
                subtitles_ass_path=ass_path if config.burn_subtitles else None,
                audio_override_path=audio_override_path,
                reframing_mode=config.reframing_mode,
                target_width=config.target_width,
                target_height=config.target_height,
            )

            video_fname = os.path.basename(output_mp4)
            srt_fname = os.path.basename(srt_path) if srt_path else None
            voice_fname = os.path.basename(audio_override_path) if audio_override_path else None
            clip_meta = {
                "id": m.id,
                "title": m.title,
                "hook": m.hook,
                "start": m.start,
                "end": m.end,
                "duration": m.duration,
                "virality_score": m.virality_score,
                "video_path": os.path.abspath(output_mp4),
                "video_filename": video_fname,
                "download_url": f"/api/shorts-cutter/jobs/{job_id}/files/{video_fname}",
                "srt_path": os.path.abspath(srt_path) if srt_path else None,
                "srt_filename": srt_fname,
                "srt_url": f"/api/shorts-cutter/jobs/{job_id}/files/{srt_fname}" if srt_fname else None,
                "voice_id": config.elevenlabs_voice_id if audio_override_path else None,
                "voiceover_filename": voice_fname,
                "voiceover_url": f"/api/shorts-cutter/jobs/{job_id}/files/{voice_fname}" if voice_fname else None,
                "size_mb": round(os.path.getsize(output_mp4) / (1024 * 1024), 2),
            }
            if story_script_meta:
                clip_meta["story_script"] = story_script_meta
            rendered_clips.append(clip_meta)

        result["clips"] = rendered_clips
        result["status"] = "COMPLETED"
        result["elapsed_seconds"] = round(time.time() - start_time, 2)
        update_progress("DONE", 100, f"Successfully created {len(rendered_clips)} shorts in {result['elapsed_seconds']}s")

    except Exception as e:
        result["status"] = "FAILED"
        result["errors"].append(str(e))
        print(f"[shorts_cutter:pipeline] Pipeline failed: {e}")
        raise

    # Save execution summary
    summary_path = os.path.join(job_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result
