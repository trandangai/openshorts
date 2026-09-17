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
        "--gemini-model", default="gemini-2.0-flash", help="Gemini model identifier (default: gemini-2.0-flash)"
    )
    parser.add_argument(
        "--mode", choices=["pillar_blur", "smart_crop"], default="pillar_blur",
        help="Reframing mode for 9:16 vertical video (default: pillar_blur)"
    )
    parser.add_argument(
        "--no-subtitles", action="store_true", help="Disable burning dynamic karaoke subtitles"
    )
    parser.add_argument(
        "--font-size", type=int, default=24, help="Subtitle font size (default: 24)"
    )

    args = parser.parse_args()

    mode = ReframingMode.SMART_CROP if args.mode == "smart_crop" else ReframingMode.PILLAR_BLUR

    config = JobConfig(
        source_input=args.input,
        output_dir=args.out,
        max_clips=args.max_clips,
        min_clip_duration=args.min_duration,
        max_clip_duration=args.max_duration,
        whisper_model_size=args.whisper_model,
        gemini_api_key=args.gemini_key,
        gemini_model=args.gemini_model,
        reframing_mode=mode,
        burn_subtitles=not args.no_subtitles,
        subtitles_font_size=args.font_size,
    )

    print("=" * 60)
    print("🎬 shorts_cutter: Starting pipeline execution")
    print(f"   Input:      {config.source_input}")
    print(f"   Mode:       {config.reframing_mode.value}")
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
