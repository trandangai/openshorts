"""
ElevenLabs voiceover and voice changing module for shorts_cutter.
Supports curated presets, fetching custom cloned voices, and synthesizing
high-quality multilingual TTS audio using standard library urllib.
"""

import os
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"

# Curated default ElevenLabs voices
DEFAULT_VOICES: List[Dict[str, Any]] = [
    {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "name": "Rachel (Female, Calm & Natural)",
        "category": "premade",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/21m00Tcm4TlvDq8ikWAM/df6788f9-1965-4d70-b790-b33f395f6f3d.mp3",
    },
    {
        "voice_id": "29vD33N1CtxCmqQRPOHJ",
        "name": "Drew (Male, Confident & Energetic)",
        "category": "premade",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/29vD33N1CtxCmqQRPOHJ/e8b52a3f-9732-440f-b78a-16d5d1e8f829.mp3",
    },
    {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "name": "Bella (Female, Soft & Expressive)",
        "category": "premade",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/EXAVITQu4vr4xnSDxMaL/04365860-244e-4f51-a9f8-7448d7c86510.mp3",
    },
    {
        "voice_id": "ErXwobaYiN019PkySvjV",
        "name": "Antoni (Male, Warm & Storyteller)",
        "category": "premade",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/ErXwobaYiN019PkySvjV/38d8f367-73e0-4729-844c-1aa16bc60fb7.mp3",
    },
    {
        "voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "name": "Josh (Male, Deep & Authoritative)",
        "category": "premade",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/TxGEqnHWrfWFTfGW9XjX/4859a857-7977-4b78-b118-8be06c7104b2.mp3",
    },
    {
        "voice_id": "yoZ06aMxZJJ28mfd3POQ",
        "name": "Sam (Male, Dynamic & Raspy)",
        "category": "premade",
        "preview_url": "https://storage.googleapis.com/eleven-public-prod/premade/voices/yoZ06aMxZJJ28mfd3POQ/1c4d417c-3411-426f-8d62-0e5503295013.mp3",
    },
]


def get_elevenlabs_voices(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch available voices from ElevenLabs API.
    If no API key provided or request fails, returns curated default presets.
    """
    if not api_key:
        return DEFAULT_VOICES

    url = f"{ELEVENLABS_API_BASE}/voices"
    req = urllib.request.Request(
        url,
        headers={"xi-api-key": api_key, "User-Agent": "shorts_cutter/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                api_voices = []
                for v in data.get("voices", []):
                    api_voices.append({
                        "voice_id": v.get("voice_id", ""),
                        "name": v.get("name", "Unnamed Voice"),
                        "category": v.get("category", "custom"),
                        "preview_url": v.get("preview_url", ""),
                        "labels": v.get("labels", {}),
                    })
                if api_voices:
                    return api_voices
    except Exception as e:
        print(f"[shorts_cutter:voiceover] Warning fetching ElevenLabs voices: {e}")

    return DEFAULT_VOICES


def generate_clip_voiceover(
    text: str,
    api_key: str,
    output_path: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    model_id: str = "eleven_flash_v2_5",
    language_code: Optional[str] = None,
) -> str:
    """
    Generate voiceover audio file using ElevenLabs TTS via standard library urllib.
    Uses eleven_flash_v2_5 (supports 32 languages including Vietnamese, with ultra-low latency).
    """
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Cannot generate voiceover for empty text")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    lang_info = f", lang='{language_code}'" if language_code else ""
    print(f"[shorts_cutter:voiceover] Generating voiceover ({len(clean_text)} chars) with voice_id '{voice_id}', model='{model_id}'{lang_info}...")

    url = f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}"
    body_data = {
        "text": clean_text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.4,
            "use_speaker_boost": True,
        },
    }
    if language_code:
        # Standardize 2-letter ISO code (e.g. 'vi', 'en', 'es')
        body_data["language_code"] = language_code.strip().lower()[:2]

    payload = json.dumps(body_data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "shorts_cutter/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120.0) as resp:
            content = resp.read()
            with open(output_path, "wb") as f:
                f.write(content)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs TTS failed ({e.code}): {err_msg}")
    except Exception as e:
        raise RuntimeError(f"ElevenLabs TTS connection error: {e}")

    print(f"[shorts_cutter:voiceover] ✅ Voiceover generated: {output_path}")
    return output_path
