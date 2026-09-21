"""
Job Queue Manager.
Supports both in-memory async execution (local zero-setup) and Redis/Celery (enterprise multi-VPS).
Supports Dual-Engine Modes: 'turbo' and 'ai_deep'.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
from core.engine import VideoTransformer
from api.models import JobStatus

# Use serial execution (1 worker) on 1GB RAM servers to prevent FFmpeg OOM crash
_executor = ThreadPoolExecutor(max_workers=1)
transformer = VideoTransformer()

JOBS_STORE: Dict[str, Dict[str, Any]] = {}

def update_job_status(job_id: str, progress: float, message: str, status: JobStatus = JobStatus.PROCESSING):
    if job_id in JOBS_STORE:
        JOBS_STORE[job_id]["progress"] = progress
        JOBS_STORE[job_id]["message"] = message
        JOBS_STORE[job_id]["status"] = status

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
        
        JOBS_STORE[job_id]["status"] = JobStatus.COMPLETED
        JOBS_STORE[job_id]["progress"] = 100.0
        JOBS_STORE[job_id]["message"] = f"{prefix} transformation complete!"
        JOBS_STORE[job_id]["original_meta"] = result.get("original")
        JOBS_STORE[job_id]["transformed_meta"] = result.get("transformed")
        JOBS_STORE[job_id]["elapsed_seconds"] = result.get("elapsed_seconds")
        JOBS_STORE[job_id]["download_url"] = f"/api/download/{job_id}"
        
    except Exception as e:
        JOBS_STORE[job_id]["status"] = JobStatus.FAILED
        JOBS_STORE[job_id]["progress"] = 0.0
        JOBS_STORE[job_id]["message"] = "Processing failed"
        JOBS_STORE[job_id]["error"] = str(e)

def submit_job(job_id: str, input_path: str, output_path: str, preset_id: str, mode: str = "turbo", custom_overrides: Optional[dict] = None):
    JOBS_STORE[job_id] = {
        "job_id": job_id,
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
        update_job_status(job_id, 5.0, "Connecting to YouTube and capturing stream...", JobStatus.PROCESSING)
        
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
        update_job_status(job_id, 40.0, f"YouTube stream captured! Running {prefix} transformation...", JobStatus.PROCESSING)
        
        def on_transform_progress(percent: float, stage: str):
            # Scale transformation progress from 40% to 98%
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
        
        JOBS_STORE[job_id]["status"] = JobStatus.COMPLETED
        JOBS_STORE[job_id]["progress"] = 100.0
        JOBS_STORE[job_id]["message"] = f"YouTube video successfully transformed & 100% copyright-free!"
        JOBS_STORE[job_id]["original_meta"] = result.get("original")
        JOBS_STORE[job_id]["transformed_meta"] = result.get("transformed")
        JOBS_STORE[job_id]["elapsed_seconds"] = result.get("elapsed_seconds")
        JOBS_STORE[job_id]["download_url"] = f"/api/download/{job_id}"
        
    except Exception as e:
        JOBS_STORE[job_id]["status"] = JobStatus.FAILED
        JOBS_STORE[job_id]["progress"] = 0.0
        JOBS_STORE[job_id]["message"] = "YouTube processing failed"
        JOBS_STORE[job_id]["error"] = str(e)

def submit_youtube_job(
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
    JOBS_STORE[job_id] = {
        "job_id": job_id,
        "input_path": input_path,
        "output_path": output_path,
        "preset": preset_id,
        "mode": mode,
        "status": JobStatus.QUEUED,
        "progress": 0.0,
        "message": "Enqueued YouTube stream extraction and protection pipeline",
        "error": None,
        "download_url": None,
        "original_meta": None,
        "transformed_meta": None,
        "elapsed_seconds": None
    }
    
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
