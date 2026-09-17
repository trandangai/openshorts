"""
Isolated FastAPI Router for shorts_cutter.
Can be mounted on existing FastAPI instances or run standalone without altering legacy routes.
"""

import os
import uuid
import asyncio
import shutil
from typing import Optional, Dict, Any
from fastapi import APIRouter, BackgroundTasks, HTTPException, Header, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from shorts_cutter.config import JobConfig, ReframingMode
from shorts_cutter.pipeline import run_pipeline
from shorts_cutter.voiceover import get_elevenlabs_voices

router = APIRouter(prefix="/api/shorts-cutter", tags=["Shorts Cutter"])

# In-memory jobs tracking store
JOBS_STORE: Dict[str, Dict[str, Any]] = {}


class ProcessRequest(BaseModel):
    input_source: str = Field(..., description="YouTube URL or server-accessible local video path")
    max_clips: int = Field(default=3, ge=1, le=30, description="Max shorts to extract")
    min_clip_duration: float = Field(default=15.0, ge=5.0, le=120.0)
    max_clip_duration: float = Field(default=60.0, ge=10.0, le=180.0)
    reframing_mode: str = Field(default="pillar_blur", description="'pillar_blur' or 'smart_crop'")
    coverage_mode: str = Field(default="part", description="'part' (viral highlights) or 'full' (sequential full video series)")
    burn_subtitles: bool = Field(default=True, description="Burn word-highlighted subtitles")
    whisper_model_size: str = Field(default="base", description="faster-whisper model: tiny, base, small")
    gemini_model: str = Field(default="gemini-2.0-flash")
    language: Optional[str] = Field(default=None, description="Spoken language code (e.g. 'en', 'es', 'fr', 'vi', 'auto')")
    translate_to_english: bool = Field(default=False, description="Translate foreign speech into English subtitles & voiceover")
    elevenlabs_voice_id: Optional[str] = Field(default=None, description="Optional ElevenLabs voice ID to replace audio")


def _run_background_job(job_id: str, config: JobConfig):
    JOBS_STORE[job_id]["status"] = "PROCESSING"
    try:
        res = run_pipeline(config)
        JOBS_STORE[job_id].update(res)
        JOBS_STORE[job_id]["status"] = "COMPLETED"
    except Exception as e:
        JOBS_STORE[job_id]["status"] = "FAILED"
        JOBS_STORE[job_id]["error"] = str(e)


@router.get("/health")
def health_check():
    """Health check endpoint for shorts_cutter module."""
    return {"status": "ok", "service": "shorts_cutter", "version": "1.0.0"}


@router.get("/voices")
def list_voices(x_elevenlabs_key: Optional[str] = Header(None, alias="X-ElevenLabs-Key")):
    """List available ElevenLabs voices (presets or live from user account)."""
    key = x_elevenlabs_key or os.environ.get("ELEVENLABS_API_KEY")
    voices = get_elevenlabs_voices(key)
    return {"voices": voices, "source": "elevenlabs" if key else "defaults"}


@router.post("/upload")
async def upload_video_file(file: UploadFile = File(...)):
    """Upload a local video file for processing."""
    uploads_dir = os.path.abspath("./output/shorts_cutter/uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    clean_name = os.path.basename(file.filename or "video.mp4")
    file_id = str(uuid.uuid4())[:8]
    dest_path = os.path.join(uploads_dir, f"{file_id}_{clean_name}")

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "file_path": dest_path,
        "filename": clean_name,
        "size_bytes": os.path.getsize(dest_path),
    }


@router.post("/process")
async def start_shorts_job(
    req: ProcessRequest,
    background_tasks: BackgroundTasks,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    x_elevenlabs_key: Optional[str] = Header(None, alias="X-ElevenLabs-Key"),
):
    """
    Start cutting shorts from a YouTube URL or video file asynchronously.
    """
    job_id = str(uuid.uuid4())[:8]
    mode = ReframingMode.SMART_CROP if req.reframing_mode == "smart_crop" else ReframingMode.PILLAR_BLUR

    config = JobConfig(
        source_input=req.input_source,
        job_id=job_id,
        output_dir="./output/shorts_cutter",
        max_clips=req.max_clips,
        min_clip_duration=req.min_clip_duration,
        max_clip_duration=req.max_clip_duration,
        whisper_model_size=req.whisper_model_size,
        gemini_api_key=x_gemini_key or os.environ.get("GEMINI_API_KEY"),
        gemini_model=req.gemini_model,
        reframing_mode=mode,
        burn_subtitles=req.burn_subtitles,
        coverage_mode=req.coverage_mode,
        language=req.language,
        translate_to_english=req.translate_to_english,
        elevenlabs_api_key=x_elevenlabs_key or os.environ.get("ELEVENLABS_API_KEY"),
        elevenlabs_voice_id=req.elevenlabs_voice_id,
    )

    JOBS_STORE[job_id] = {
        "job_id": job_id,
        "status": "QUEUED",
        "input_source": req.input_source,
        "coverage_mode": req.coverage_mode,
        "elevenlabs_voice_id": req.elevenlabs_voice_id,
        "created_at": asyncio.get_event_loop().time(),
    }

    background_tasks.add_task(_run_background_job, job_id, config)

    return {
        "job_id": job_id,
        "status": "QUEUED",
        "message": "Shorts processing queued successfully in background",
    }


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """Query progress, transcript, and generated clips for a job."""
    job = JOBS_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.api_route("/jobs/{job_id}/files/{filename}", methods=["GET", "HEAD"])
def download_clip_file(job_id: str, filename: str):
    """Download or stream generated clip MP4 or subtitle file."""
    # 1. Check if job in memory has explicit file path
    found_path = None
    job = JOBS_STORE.get(job_id)
    if job and "clips" in job:
        for c in job["clips"]:
            if os.path.basename(c.get("video_path", "")) == filename:
                found_path = c.get("video_path")
                break
            if c.get("srt_path") and os.path.basename(c["srt_path"]) == filename:
                found_path = c["srt_path"]
                break

    # 2. Check standard directory
    if not found_path or not os.path.exists(found_path):
        job_dir = os.path.abspath(f"./output/shorts_cutter/job_{job_id}")
        direct_candidate = os.path.join(job_dir, "clips", filename)
        if os.path.exists(direct_candidate):
            found_path = direct_candidate
        elif os.path.exists(os.path.join(job_dir, filename)):
            found_path = os.path.join(job_dir, filename)
        elif os.path.exists(job_dir):
            # 3. Recursive search to find nested job outputs
            for root, _, files in os.walk(job_dir):
                if filename in files:
                    found_path = os.path.join(root, filename)
                    break

    if not found_path or not os.path.exists(found_path):
        raise HTTPException(status_code=404, detail=f"Requested file '{filename}' not found for job '{job_id}'")

    media_type = "video/mp4" if filename.endswith(".mp4") else "text/plain"
    return FileResponse(
        found_path,
        media_type=media_type,
        filename=filename,
        headers={"Accept-Ranges": "bytes"}
    )


# Standalone application export
from fastapi import FastAPI
standalone_app = FastAPI(title="Shorts Cutter API", version="1.0.0")
standalone_app.include_router(router)
