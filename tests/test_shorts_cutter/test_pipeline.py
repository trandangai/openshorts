"""
Unit and integration tests for shorts_cutter using standard unittest.
"""

import os
import shutil
import tempfile
import unittest

from shorts_cutter.config import (
    JobConfig,
    ReframingMode,
    Transcript,
    Segment,
    WordTimestamp,
    ViralMoment,
)
from shorts_cutter.ingest import is_url, probe_video
from shorts_cutter.subtitles import (
    _format_ass_timestamp,
    _format_srt_timestamp,
    extract_clip_words,
    generate_ass_subtitles,
    generate_srt_subtitles,
)
from shorts_cutter.analyzer import _extract_json, _heuristic_analyze_moments
from shorts_cutter.reframer import build_reframing_filter
try:
    from fastapi.testclient import TestClient
    from shorts_cutter.router import standalone_app
    HAS_FASTAPI = True
except ImportError:
    TestClient = None
    standalone_app = None
    HAS_FASTAPI = False


class TestShortsCutter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_config_defaults(self):
        cfg = JobConfig(source_input="test.mp4")
        self.assertEqual(cfg.target_width, 1080)
        self.assertEqual(cfg.target_height, 1920)
        self.assertEqual(cfg.reframing_mode, ReframingMode.PILLAR_BLUR)
        self.assertTrue(cfg.burn_subtitles)
        self.assertEqual(cfg.max_clips, 3)
        self.assertIsNone(cfg.language)
        self.assertFalse(cfg.translate_to_english)

        cfg_es = JobConfig(source_input="test.mp4", language="es", translate_to_english=True)
        self.assertEqual(cfg_es.language, "es")
        self.assertTrue(cfg_es.translate_to_english)

    def test_is_url(self):
        self.assertTrue(is_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(is_url("http://example.com/video.mp4"))
        self.assertFalse(is_url("/path/to/local/file.mp4"))
        self.assertFalse(is_url("relative/path/video.mp4"))

    def test_probe_video_missing(self):
        with self.assertRaises(FileNotFoundError):
            probe_video("/nonexistent/video/path.mp4")

    def test_probe_video_valid(self):
        sample_path = "/app/demo-openshorts.mp4"
        if not os.path.exists(sample_path):
            sample_path = "demo-openshorts.mp4"
        if os.path.exists(sample_path):
            meta = probe_video(sample_path)
            self.assertEqual(meta["width"], 1920)
            self.assertEqual(meta["height"], 1080)
            self.assertGreater(meta["fps"], 0)
            self.assertGreater(meta["duration"], 0)

    def test_subtitle_timestamp_formatting(self):
        # ASS timestamp: H:MM:SS.cc
        self.assertEqual(_format_ass_timestamp(0.0), "0:00:00.00")
        self.assertEqual(_format_ass_timestamp(65.45), "0:01:05.45")
        self.assertEqual(_format_ass_timestamp(3661.2), "1:01:01.20")

        # SRT timestamp: HH:MM:SS,mmm
        self.assertEqual(_format_srt_timestamp(0.0), "00:00:00,000")
        self.assertEqual(_format_srt_timestamp(65.45), "00:01:05,450")

    def test_extract_clip_words(self):
        transcript = Transcript(
            full_text="Hello world this is a test clip",
            language="en",
            duration=30.0,
            segments=[
                Segment(
                    id=0,
                    start=5.0,
                    end=15.0,
                    text="Hello world this is a test",
                    words=[
                        WordTimestamp(word="Hello", start=5.0, end=6.0),
                        WordTimestamp(word="world", start=6.2, end=7.0),
                        WordTimestamp(word="this", start=7.2, end=8.0),
                        WordTimestamp(word="is", start=8.2, end=9.0),
                        WordTimestamp(word="a", start=9.1, end=9.5),
                        WordTimestamp(word="test", start=9.6, end=10.5),
                    ],
                )
            ],
        )

        clip_words = extract_clip_words(transcript, clip_start=6.0, clip_end=10.0)
        self.assertEqual(len(clip_words), 5)
        # Check rebasing to 0.0s
        self.assertEqual(clip_words[0].word, "world")
        self.assertEqual(round(clip_words[0].start, 2), 0.2)
        self.assertEqual(clip_words[1].word, "this")

    def test_ass_and_srt_generation(self):
        words = [
            WordTimestamp(word="Hello", start=0.0, end=1.0),
            WordTimestamp(word="World", start=1.1, end=2.0),
            WordTimestamp(word="Shorts", start=2.1, end=3.0),
        ]
        ass_path = os.path.join(self.temp_dir, "test.ass")
        srt_path = os.path.join(self.temp_dir, "test.srt")

        generate_ass_subtitles(words, ass_path)
        generate_srt_subtitles(words, srt_path)

        self.assertTrue(os.path.exists(ass_path))
        self.assertTrue(os.path.exists(srt_path))

        with open(ass_path, "r", encoding="utf-8") as f:
            ass_content = f.read()
        self.assertIn("[Script Info]", ass_content)
        self.assertIn("Dialogue:", ass_content)

        with open(srt_path, "r", encoding="utf-8") as f:
            srt_content = f.read()
        self.assertIn("00:00:00,000 --> 00:00:03,000", srt_content)

    def test_heuristic_moment_analyzer(self):
        segments = [
            Segment(
                id=i,
                start=i * 5.0,
                end=(i + 1) * 5.0,
                text=f"This is segment number {i} with engaging content.",
                words=[
                    WordTimestamp(word="This", start=i * 5.0, end=i * 5.0 + 1.0),
                    WordTimestamp(word="content", start=i * 5.0 + 1.1, end=(i + 1) * 5.0),
                ],
            )
            for i in range(10)
        ]
        transcript = Transcript(
            full_text="Test transcript with 50 seconds",
            language="en",
            duration=50.0,
            segments=segments,
        )

        moments = _heuristic_analyze_moments(transcript, max_clips=2, min_duration=15.0, max_duration=25.0)
        self.assertGreater(len(moments), 0)
        self.assertGreaterEqual(moments[0].duration, 15.0)
        self.assertGreater(moments[0].virality_score, 0)

    def test_reframer_filters(self):
        pb = build_reframing_filter(ReframingMode.PILLAR_BLUR, 1920, 1080, 1080, 1920)
        self.assertIn("boxblur", pb)
        self.assertIn("1080:1920", pb)

        sc = build_reframing_filter(ReframingMode.SMART_CROP, 1920, 1080, 1080, 1920, crop_center_x=0.5)
        self.assertIn("crop=", sc)
        self.assertIn("scale=1080:1920", sc)

    def test_router_health(self):
        if not HAS_FASTAPI:
            self.skipTest("fastapi not installed in current environment")
        client = TestClient(standalone_app)
        response = client.get("/api/shorts-cutter/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "shorts_cutter")

    def test_router_job_not_found(self):
        if not HAS_FASTAPI:
            self.skipTest("fastapi not installed in current environment")
        client = TestClient(standalone_app)
        response = client.get("/api/shorts-cutter/jobs/nonexistent-id")
        self.assertEqual(response.status_code, 404)

    def test_heuristic_full_series_coverage(self):
        segments = [
            Segment(
                id=i,
                start=i * 10.0,
                end=(i + 1) * 10.0,
                text=f"This is sentence {i} explaining topic {i}.",
                words=[
                    WordTimestamp(word="This", start=i * 10.0, end=i * 10.0 + 1.0),
                    WordTimestamp(word="topic", start=i * 10.0 + 1.1, end=(i + 1) * 10.0),
                ],
            )
            for i in range(12)  # 120 seconds total
        ]
        transcript = Transcript(
            full_text="120 seconds full transcript",
            language="en",
            duration=120.0,
            segments=segments,
        )

        parts = _heuristic_analyze_moments(
            transcript,
            max_clips=10,
            min_duration=20.0,
            max_duration=40.0,
            coverage_mode="full",
        )

        self.assertGreaterEqual(len(parts), 3)
        # Verify sequential Part naming
        self.assertTrue(parts[0].title.startswith("Part 1:"))
        self.assertTrue(parts[1].title.startswith("Part 2:"))
        self.assertTrue(parts[2].title.startswith("Part 3:"))

        # Verify contiguous boundaries (no gaps between parts)
        self.assertAlmostEqual(parts[0].start, 0.0)
        self.assertAlmostEqual(parts[1].start, parts[0].end)
        self.assertAlmostEqual(parts[2].start, parts[1].end)

    def test_router_process_endpoint_coverage_mode(self):
        if not HAS_FASTAPI:
            self.skipTest("fastapi not installed in current environment")
        client = TestClient(standalone_app)
        response = client.post(
            "/api/shorts-cutter/process",
            json={
                "input_source": "demo-openshorts.mp4",
                "coverage_mode": "full",
                "max_clips": 10,
                "min_clip_duration": 15.0,
                "max_clip_duration": 60.0,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "QUEUED")
        self.assertIn("job_id", data)

    def test_voiceover_default_voices(self):
        from shorts_cutter.voiceover import get_elevenlabs_voices, DEFAULT_VOICES
        voices = get_elevenlabs_voices(None)
        self.assertGreaterEqual(len(voices), 6)
        self.assertEqual(voices[0]["voice_id"], "21m00Tcm4TlvDq8ikWAM")
        self.assertIn("Rachel", voices[0]["name"])

    def test_router_voices_endpoint(self):
        if not HAS_FASTAPI:
            self.skipTest("fastapi not installed in current environment")
        client = TestClient(standalone_app)
        response = client.get("/api/shorts-cutter/voices")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("voices", data)
        self.assertGreaterEqual(len(data["voices"]), 6)


if __name__ == "__main__":
    unittest.main()
