"""
Command-line interface (CLI) for shorts_cutter.

Usage:
    python -m shorts_cutter.cli --input demo.mp4 --out ./output/my_shorts
    python -m shorts_cutter.cli --input "https://www.youtube.com/watch?v=..." --mode smart_crop --max-clips 3
"""

import argparse
import sys
import json
from shorts_cutter.config import JobConfig, ReframingMode
from shorts_cutter.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="shorts_cutter: Cut YouTube videos or local video files into viral 9:16 Shorts at zero cost."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="YouTube video URL or local file path (.mp4, .mov, .mkv)"
    )
    parser.add_argument(
        "-o", "--out", default="./output/shorts_cutter", help="Output directory for generated shorts"
    )
    parser.add_argument(
        "--max-clips", type=int, default=3, help="Maximum number of shorts to extract (default: 3)"
    )
    parser.add_argument(
        "--min-duration", type=float, default=15.0, help="Minimum clip duration in seconds (default: 15.0)"
    )
    parser.add_argument(
        "--max-duration", type=float, default=60.0, help="Maximum clip duration in seconds (default: 60.0)"
    )
    parser.add_argument(
        "--whisper-model", default="base", choices=["tiny", "base", "small", "medium", "large-v3"],
        help="faster-whisper model size (default: base)"
    )
    parser.add_argument(
        "--gemini-key", default=None, help="Google Gemini API Key (optional, defaults to env or offline heuristic)"
    )
    parser.add_argument(
        "--gemini-model", default=os.environ.get("GEMINI_MODEL") or "gemini-3.1-flash", help="Gemini model identifier (default: gemini-3.1-flash)"
    )
    parser.add_argument(
        "--mode", choices=["pillar_blur", "smart_crop"], default="pillar_blur",
        help="Reframing mode for 9:16 vertical video (default: pillar_blur)"
    )
    parser.add_argument(
        "--coverage", choices=["part", "full"], default="part",
        help="Coverage mode: 'part' for viral highlights or 'full' for sequential chronological series (default: part)"
    )
    parser.add_argument(
        "--elevenlabs-key", default=None,
        help="ElevenLabs API key for AI voiceover / voice changing"
    )
    parser.add_argument(
        "--voice-id", default=None,
        help="ElevenLabs voice ID to replace video audio (e.g. 21m00Tcm4TlvDq8ikWAM for Rachel)"
    )
    parser.add_argument(
        "--language", "-l", default=None,
        help="Spoken language code for Whisper transcription (e.g. 'en', 'es', 'fr', 'vi', 'ja', default: auto-detect)"
    )
    parser.add_argument(
        "--translate", action="store_true",
        help="Translate foreign language speech into English subtitles and voiceover"
    )
    parser.add_argument(
        "--kids-story", action="store_true",
        help="Adapt transcript into rhythmic children's storytelling script (±5 words rule)"
    )
    parser.add_argument(
        "--watermark", default="assets/logo_maf_1.png",
        help="Path to brand logo watermark PNG image (default: assets/logo_maf_1.png)"
    )
    parser.add_argument(
        "--no-watermark", action="store_true",
        help="Disable stamping brand watermark logo on clips"
    )
    parser.add_argument(
        "--font-size", type=int, default=24, help="Subtitle font size (default: 24)"
    )

    args = parser.parse_args()

    mode = ReframingMode.SMART_CROP if args.mode == "smart_crop" else ReframingMode.PILLAR_BLUR

    # In full series mode, if user didn't change default max_clips, increase it to 20
    max_clips = args.max_clips
    if args.coverage == "full" and max_clips == 3:
        max_clips = 20

    config = JobConfig(
        source_input=args.input,
        output_dir=args.out,
        max_clips=max_clips,
        min_clip_duration=args.min_duration,
        max_clip_duration=args.max_duration,
        whisper_model_size=args.whisper_model,
        gemini_api_key=args.gemini_key,
        gemini_model=args.gemini_model,
        reframing_mode=mode,
        burn_subtitles=not args.no_subtitles,
        subtitles_font_size=args.font_size,
        coverage_mode=args.coverage,
        language=args.language,
        translate_to_english=args.translate,
        kids_storytelling_mode=args.kids_story,
        elevenlabs_api_key=args.elevenlabs_key,
        elevenlabs_voice_id=args.voice_id,
        watermark_path=None if args.no_watermark else args.watermark,
    )

    print("=" * 60)
    print("🎬 shorts_cutter: Starting pipeline execution")
    print(f"   Input:      {config.source_input}")
    print(f"   Mode:       {config.reframing_mode.value}")
    print(f"   Coverage:   {config.coverage_mode.upper()} ({'Sequential Full Video' if config.coverage_mode == 'full' else 'Viral Highlights'})")
    if config.elevenlabs_voice_id:
        print(f"   Voiceover:  ElevenLabs (voice_id: {config.elevenlabs_voice_id})")
    print(f"   Clips Max:  {config.max_clips} ({config.min_clip_duration}s - {config.max_clip_duration}s)")
    print(f"   Output Dir: {config.output_dir}")
    print("=" * 60)

    try:
        result = run_pipeline(config)
        print("\n" + "=" * 60)
        print("🎉 SUCCESS: Processing completed!")
        print(f"   Job ID:     {result['job_id']}")
        print(f"   Time Taken: {result['elapsed_seconds']}s")
        print(f"   Clips Generated: {len(result['clips'])}")
        for c in result["clips"]:
            print(f"     • [#{c['id']}] {c['title']} ({c['duration']}s) -> {c['video_path']}")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
