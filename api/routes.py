import os
import uuid
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles

from api.config import INPUT_DIR, OUTPUT_DIR, ALLOWED_EXTENSIONS
from api.models import JobResponse, JobStatus
from core.presets import PRESETS
from workers.manager import submit_job, JOBS_STORE

router = APIRouter()

@router.get("/presets")
async def get_presets():
    return list(PRESETS.values())

@router.post("/upload", response_model=JobResponse)
async def upload_video(
    file: UploadFile = File(...),
    preset: str = Form("stealth_deep"),
    mode: str = Form("turbo"),
    custom_settings: Optional[str] = Form(None)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    if preset not in PRESETS:
        preset = "stealth_deep"
        
    if mode not in ["turbo", "ai_deep"]:
        mode = "turbo"
        
    custom_overrides = None
    if custom_settings:
        try:
            custom_overrides = json.loads(custom_settings)
        except Exception:
            custom_overrides = None
            
    job_id = str(uuid.uuid4())
    safe_name = f"{job_id}{ext}"
    input_path = os.path.join(INPUT_DIR, safe_name)
    output_path = os.path.join(OUTPUT_DIR, f"safe_{job_id}.mp4")
    
    # Stream large uploads in chunks
    async with aiofiles.open(input_path, "wb") as f:
        while chunk := await file.read(1024 * 1024 * 4): # 4MB chunks
            await f.write(chunk)
            
    # Submit to worker queue
    submit_job(job_id, input_path, output_path, preset, mode, custom_overrides)
    
    return JobResponse(
        job_id=job_id,
        filename=file.filename,
        status=JobStatus.QUEUED,
        progress=0.0,
        message=f"Video uploaded successfully and queued for {'Turbo DSP' if mode == 'turbo' else 'AI Deep Studio'} transformation",
        preset=preset
    )

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    if job_id not in JOBS_STORE:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = JOBS_STORE[job_id]
    return JobResponse(
        job_id=job_id,
        filename=os.path.basename(job.get("input_path", "video.mp4")),
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        preset=job["preset"],
        download_url=job.get("download_url"),
        original_meta=job.get("original_meta"),
        transformed_meta=job.get("transformed_meta"),
        elapsed_seconds=job.get("elapsed_seconds"),
        error=job.get("error")
    )

@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str):
    if job_id not in JOBS_STORE:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        while True:
            if job_id not in JOBS_STORE:
                break
            job = JOBS_STORE[job_id]
            
            data = json.dumps({
                "status": job["status"].value,
                "progress": job["progress"],
                "message": job["message"],
                "download_url": job.get("download_url"),
                "elapsed": job.get("elapsed_seconds")
            })
            yield f"data: {data}\n\n"
            
            if job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED]:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.api_route("/download/{job_id}", methods=["GET", "HEAD"])
async def download_processed_video(job_id: str):
    output_path = os.path.join(OUTPUT_DIR, f"safe_{job_id}.mp4")
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Processed video not found or expired")
        
    return FileResponse(
        path=output_path,
        filename=f"safe_{job_id[:8]}.mp4",
        media_type="video/mp4"
    )

@router.get("/health")
async def health_check():
    import shutil
    total, used, free = shutil.disk_usage(OUTPUT_DIR)
    return {
        "status": "healthy",
        "active_jobs": len([j for j in JOBS_STORE.values() if j["status"] == JobStatus.PROCESSING]),
        "storage": {
            "free_gb": round(free / (1024**3), 2),
            "total_gb": round(total / (1024**3), 2)
        }
    }
