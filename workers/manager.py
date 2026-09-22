"""
Job Queue Manager.
Supports both in-memory async execution and SQLite persistence across server restarts / browser closes.
Supports Dual-Engine Modes: 'turbo' and 'ai_deep'.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
from core.engine import VideoTransformer
from api.models import JobStatus
from core.db import db_save_job, db_update_job_status, db_get_job

# Use serial execution (1 worker) on 1GB RAM servers to prevent FFmpeg OOM crash
_executor = ThreadPoolExecutor(max_workers=1)
transformer = VideoTransformer()

JOBS_STORE: Dict[str, Dict[str, Any]] = {}

def get_job_state(job_id: str) -> Optional[Dict[str, Any]]:
    """Gets job state from memory cache, falling back to SQLite database."""
    if job_id in JOBS_STORE:
        return JOBS_STORE[job_id]
    db_job = db_get_job(job_id)
    if db_job:
        JOBS_STORE[job_id] = {
            "job_id": db_job["job_id"],
            "user_id": db_job.get("user_id"),
            "filename": db_job.get("filename", "video.mp4"),
            "input_path": f"storage/inputs/{db_job['job_id']}.mp4",
            "output_path": f"storage/outputs/safe_{db_job['job_id']}.mp4",
            "preset": db_job.get("preset", "stealth_deep"),
            "mode": db_job.get("mode", "turbo"),
            "status": JobStatus(db_job["status"]) if db_job["status"] in JobStatus._value2member_map_ else JobStatus.QUEUED,
            "progress": float(db_job.get("progress", 0.0) or 0.0),
            "message": db_job.get("message", ""),
            "error": db_job.get("error"),
            "download_url": db_job.get("download_url"),
            "original_meta": db_job.get("original_meta"),
            "transformed_meta": db_job.get("transformed_meta"),
            "elapsed_seconds": db_job.get("elapsed_seconds")
        }
        return JOBS_STORE[job_id]
    return None

def update_job_status(
    job_id: str,
    progress: float,
    message: str,
    status: JobStatus = JobStatus.PROCESSING,
    error: Optional[str] = None,
    download_url: Optional[str] = None,
    original_meta: Optional[dict] = None,
    transformed_meta: Optional[dict] = None,
    elapsed_seconds: Optional[float] = None
):
    if job_id in JOBS_STORE:
        JOBS_STORE[job_id]["progress"] = progress
        JOBS_STORE[job_id]["message"] = message
        JOBS_STORE[job_id]["status"] = status
        if error is not None:
            JOBS_STORE[job_id]["error"] = error
        if download_url is not None:
            JOBS_STORE[job_id]["download_url"] = download_url
        if original_meta is not None:
            JOBS_STORE[job_id]["original_meta"] = original_meta
        if transformed_meta is not None:
            JOBS_STORE[job_id]["transformed_meta"] = transformed_meta
        if elapsed_seconds is not None:
            JOBS_STORE[job_id]["elapsed_seconds"] = elapsed_seconds

    # Sync to persistent SQLite database
    try:
        st_val = status.value if hasattr(status, "value") else str(status)
        db_update_job_status(
            job_id=job_id,
            status=st_val,
            progress=progress,
            message=message,
            error=error,
            download_url=download_url,
            original_meta=original_meta,
            transformed_meta=transformed_meta,
            elapsed_seconds=elapsed_seconds
        )
    except Exception as dbe:
        print(f"DB update error for {job_id}: {dbe}")

def _sync_worker(job_id: str, input_path: str, output_path: str, preset_id: str, mode: str = "turbo", custom_overrides: Optional[dict] = None):
    try:
        prefix = "⚡ Turbo DSP" if mode == "turbo" else "🧠 AI Deep Studio"
        update_job_status(job_id, 5.0, f"Starting {prefix} transformation engine...", JobStatus.PROCESSING)
        
        def on_progress(percent: float, stage: str):
            update_job_status(job_id, percent, stage, JobStatus.PROCESSING)
            
        result = transformer.process(
            input_path=input_path,
            output_path=output_path,
            preset_id=preset_id,
            mode=mode,
            custom_overrides=custom_overrides,
            progress_callback=on_progress
        )
        
        update_job_status(
            job_id=job_id,
            progress=100.0,
            message=f"{prefix} transformation complete!",
            status=JobStatus.COMPLETED,
            download_url=f"/api/download/{job_id}",
            original_meta=result.get("original"),
            transformed_meta=result.get("transformed"),
            elapsed_seconds=result.get("elapsed_seconds")
        )
        
    except Exception as e:
        update_job_status(
            job_id=job_id,
            progress=0.0,
            message=f"Processing failed: {str(e)}",
            status=JobStatus.FAILED,
            error=str(e)
        )

def submit_job(
    job_id: str,
    input_path: str,
    output_path: str,
    preset_id: str,
    mode: str = "turbo",
    custom_overrides: Optional[dict] = None,
    user_id: Optional[int] = None,
    filename: Optional[str] = None
):
    fn = filename or os.path.basename(input_path)
    JOBS_STORE[job_id] = {
        "job_id": job_id,
        "user_id": user_id,
        "filename": fn,
        "input_path": input_path,
        "output_path": output_path,
        "preset": preset_id,
        "mode": mode,
        "status": JobStatus.QUEUED,
        "progress": 0.0,
        "message": "Enqueued in processing pipeline",
        "error": None,
        "download_url": None,
        "original_meta": None,
        "transformed_meta": None,
        "elapsed_seconds": None
    }
    try:
        db_save_job(job_id, user_id, fn, preset_id, mode, status="queued")
    except Exception as e:
        print(f"DB save error for {job_id}: {e}")
    
    _executor.submit(_sync_worker, job_id, input_path, output_path, preset_id, mode, custom_overrides)

def _youtube_worker(
    job_id: str,
    youtube_url: str,
    input_path: str,
    output_path: str,
    start_sec: float,
    end_sec: Optional[float],
    preset_id: str,
    mode: str = "turbo",
    custom_overrides: Optional[dict] = None
):
    try:
        from core.youtube_service import download_and_trim_youtube
        update_job_status(job_id, 5.0, "Connecting to stream and capturing clip...", JobStatus.PROCESSING)
        
        def on_download_progress(pct: float, msg: str):
            update_job_status(job_id, pct * 0.4, msg, JobStatus.PROCESSING)
            
        download_and_trim_youtube(
            url=youtube_url,
            output_path=input_path,
            start_sec=start_sec,
            end_sec=end_sec,
            progress_callback=on_download_progress
        )
        
        prefix = "⚡ Turbo DSP" if mode == "turbo" else "🧠 AI Deep Studio"
        update_job_status(job_id, 40.0, f"Stream clip captured! Running {prefix} transformation...", JobStatus.PROCESSING)
        
        def on_transform_progress(percent: float, stage: str):
            scaled = 40.0 + (percent * 0.58)
            update_job_status(job_id, min(scaled, 98.0), stage, JobStatus.PROCESSING)
            
        result = transformer.process(
            input_path=input_path,
            output_path=output_path,
            preset_id=preset_id,
            mode=mode,
            custom_overrides=custom_overrides,
            progress_callback=on_transform_progress
        )
        
        update_job_status(
            job_id=job_id,
            progress=100.0,
            message="Stream video successfully transformed & 100% copyright-free!",
            status=JobStatus.COMPLETED,
            download_url=f"/api/download/{job_id}",
            original_meta=result.get("original"),
            transformed_meta=result.get("transformed"),
            elapsed_seconds=result.get("elapsed_seconds")
        )
        
    except Exception as e:
        update_job_status(
            job_id=job_id,
            progress=0.0,
            message=f"Stream processing failed: {str(e)}",
            status=JobStatus.FAILED,
            error=str(e)
        )

def submit_youtube_job(
    job_id: str,
    youtube_url: str,
    input_path: str,
    output_path: str,
    start_sec: float,
    end_sec: Optional[float],
    preset_id: str,
    mode: str = "turbo",
    custom_overrides: Optional[dict] = None,
    user_id: Optional[int] = None,
    title: Optional[str] = None
):
    fn = title or f"Stream_{job_id[:6]}.mp4"
    JOBS_STORE[job_id] = {
        "job_id": job_id,
        "user_id": user_id,
        "filename": fn,
        "input_path": input_path,
        "output_path": output_path,
        "preset": preset_id,
        "mode": mode,
        "status": JobStatus.QUEUED,
        "progress": 0.0,
        "message": "Enqueued stream extraction and protection pipeline",
        "error": None,
        "download_url": None,
        "original_meta": None,
        "transformed_meta": None,
        "elapsed_seconds": None
    }
    try:
        db_save_job(job_id, user_id, fn, preset_id, mode, status="queued")
    except Exception as e:
        print(f"DB save error for {job_id}: {e}")
    
    _executor.submit(
        _youtube_worker,
        job_id,
        youtube_url,
        input_path,
        output_path,
        start_sec,
        end_sec,
        preset_id,
        mode,
        custom_overrides
    )
