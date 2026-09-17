# OpenShorts Cost Optimization & 3rd-Party Reduction Guide

This document provides a comprehensive guide to understanding costs across OpenShorts, eliminating unnecessary 3rd-party subscription/API fees, and running the platform at minimum or zero cost.

---

## 1. 3rd-Party Services Overview & Cost Breakdown

| Service | Used In | Purpose | Typical Cost | Free Tier Available? |
| :--- | :--- | :--- | :--- | :--- |
| **fal.ai** | AI Shorts (`saasshorts.py`) | Actor generation (Flux Pro), Talking Head (Kling / Hailuo + VEED Lipsync), B-Roll | ~$0.39 - $2.10 per video | Pay-as-you-go ($10 credit starter) |
| **ElevenLabs** | AI Shorts & Dubbing (`saasshorts.py`, `translate.py`) | Voiceover TTS and audio translation | ~$0.10 - $0.30 per minute | Free tier (10,000 chars/mo) |
| **Google Gemini** | Core Clipping & AI Shorts (`gemini_worker.py`, `editor.py`) | Viral moment selection, transcript scoring, hook generation, scriptwriting | ~$0.0001 - $0.005 per video (Gemini 2.0 / 3.1 Flash-Lite) | **Yes: 1,500 free requests/day** |
| **AWS S3** | Storage (`s3_uploader.py`) | Cloud video and thumbnail asset caching | ~$0.023 / GB | 5 GB Free for 12 months |
| **Upload-Post** | Social Distribution (`app.py`) | Auto-posting to TikTok, YouTube, IG | Subscription / per post | Optional |

---

## 2. Core Video Clipping: How to Run for $0 Cost

If your goal is to **cut YouTube videos or uploaded files into vertical Shorts**:
> [!TIP]
> **You do NOT need fal.ai or ElevenLabs at all!**
> OpenShorts core video clipping can be run **100% free of charge**.

### The Zero-Cost Architecture for Video Clipping:
1. **Video Ingestion**: `yt-dlp` (open-source, 100% free) downloads YouTube videos or handles direct file uploads locally.
2. **Transcription**: `faster-whisper` runs locally inside Docker or on host CPU/GPU (100% free, no OpenAI Whisper API billing).
3. **Viral Moment Detection**: Google Gemini 3.1 Flash-Lite (`gemini-3.1-flash-lite` or `gemini-2.0-flash`).
   - The Google AI Studio free tier provides **1,500 requests per day** with no credit card charges.
   - A typical 20-minute video uses 1–2 requests. You can process hundreds of videos daily for **$0**.
4. **Framing & Scene Detection**: PySceneDetect + OpenCV / YOLOv8 (runs locally for free).
5. **Video Rendering & Subtitle Burn**: FFmpeg + Remotion (runs locally for free).

---

## 3. Saving Costs on the "AI Shorts" Generator (fal.ai Replacement Strategy)

If you plan to use synthetic AI Shorts generation, `fal.ai` is the primary cost driver. Here is how to reduce or eliminate fal.ai expenses:

### Strategy A: Built-in Low-Cost Mode (Instant 70% Savings)
- OpenShorts has a built-in low-cost route in `saasshorts.py`:
  - **Premium mode (Kling Avatar v2)**: ~$1.69 - $2.00 / video.
  - **Low-Cost mode (Hailuo 2.3 Fast + VEED Lipsync)**: ~$0.39 / video.
- Simply set or call low-cost mode to cut fal.ai bills by >70% without changing code.

### Strategy B: Replace Actor & B-Roll Images with Google Imagen 3 (Via Existing Gemini Key)
- **Current**: Flux 2 Pro on fal.ai (~$0.05 per image option).
- **Alternative**: Use Google Imagen 3 (`imagen-3.0-generate-002`) via your existing `GEMINI_API_KEY`.
- **Cost**: ~$0.03 per image or free promo credits through Google Cloud, removing image dependencies from fal.ai.

### Strategy C: Replace AI B-Roll with Free Stock Video APIs
- **Current**: Generates AI images on fal.ai with zoom animations.
- **Alternative**: Query **Pexels API** or **Pixabay API** using script keywords.
- **Cost**: **100% Free** (generous API limits: 200 requests/hour for Pexels). Real video clips often convert better than AI stills.

### Strategy D: Self-Host Open-Source Talking Head / Lip-Sync Models
The talking avatar is 85% of the cost. You can replace cloud services with self-hosted open-source models:
- **Models**:
  - **LivePortrait**: High-speed portrait animation with micro-expressions.
  - **MuseTalk / SadTalker**: Audio-driven lip-synchronization.
- **Where to run**:
  - **Local GPU** (NVIDIA RTX 3060/3080/4070 or M-series Mac via PyTorch MPS): **$0 marginal cost**.
  - **Cloud Spot GPU (RunPod / Vast.ai)**: An RTX 4090 or RTX 3090 instance costs **$0.22 - $0.34/hour**. You can render ~30-50 videos per hour, dropping per-video cost from **$1.69 down to ~$0.01**.

---

## 4. Replacing ElevenLabs with Free Text-to-Speech (TTS)

If generating voiceovers:
- **Current**: ElevenLabs costs ~$0.10 - $0.30/video.
- **Zero-Cost Alternatives**:
  1. **Edge-TTS (`edge-tts`)**:
     - Python library tapping into Microsoft Edge's neural TTS.
     - Natural human voices (e.g., Guy, Christopher, Jenny, multilingual).
     - **Cost**: 100% Free, no API key required.
  2. **ChatTTS / Piper / Coqui TTS**:
     - Local open-source neural TTS models running on CPU/GPU.
     - **Cost**: 100% Free.

---

## 5. Storage Cost Optimization

- **Default**: AWS S3 standard storage charges for data storage and egress.
- **Optimized Alternatives**:
  - **Local Storage**: For self-hosted instances, save output to `./output` or mounted volume ($0).
  - **Cloudflare R2**: S3-compatible API with **zero egress fees** and a 10 GB free tier.

---

## 6. Actionable Cost Checklist

- [x] **Core Video Clipping**: Run purely on local Whisper + free Gemini tier ($0/mo).
- [ ] **AI Shorts Actor & B-Roll**: Route image generation to Google Imagen 3 or Pexels API.
- [ ] **Voice Generation**: Transition from ElevenLabs to Edge-TTS for free neural voices.
- [ ] **Avatar Generation**: Evaluate local LivePortrait/MuseTalk container or low-cost fal.ai Hailuo mode.
- [ ] **Storage**: Use local storage or Cloudflare R2 instead of standard paid S3.
