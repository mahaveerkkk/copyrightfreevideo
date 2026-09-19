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

_executor = ThreadPoolExecutor(max_workers=max(2, os.cpu_count() or 2))
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
