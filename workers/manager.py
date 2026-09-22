"""
Job Queue Manager.
Supports in-memory async execution, SQLite persistence across server restarts / browser closes,
interactive cancellation, and automatic multi-part batch splitting.
"""

import os
import uuid
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, List
from core.engine import VideoTransformer, ACTIVE_PROCESSES
from api.models import JobStatus
from core.db import db_save_job, db_update_job_status, db_get_job, get_db_connection

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
            "elapsed_seconds": db_job.get("elapsed_seconds"),
            "batch_id": db_job.get("batch_id")
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

def cancel_job(job_id: str) -> bool:
    """Terminates active rendering subprocess, updates status to cancelled, and purges partial files."""
    # 1. Terminate subprocess if active
    proc = ACTIVE_PROCESSES.get(job_id)
    if proc:
        try:
            proc.kill()
        except Exception:
            pass
        ACTIVE_PROCESSES.pop(job_id, None)

    # 2. Update status to cancelled in memory and DB
    update_job_status(
        job_id=job_id,
        progress=0.0,
        message="🛑 Job cancelled by user",
        status=JobStatus.FAILED,
        error="Cancelled by user"
    )

    # 3. Purge partial files from disk
    from api.config import OUTPUT_DIR, INPUT_DIR, TEMP_DIR
    for folder in [OUTPUT_DIR, INPUT_DIR, TEMP_DIR]:
        if not os.path.exists(folder): continue
        for f in os.listdir(folder):
            if job_id in f:
                try:
                    fpath = os.path.join(folder, f)
                    if os.path.isfile(fpath): os.remove(fpath)
                    elif os.path.isdir(fpath): shutil.rmtree(fpath, ignore_errors=True)
                except Exception:
                    pass
    return True

def cancel_batch(batch_id: str) -> int:
    """Cancels all queued or running jobs associated with a batch."""
    cancelled_count = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT job_id FROM render_jobs WHERE batch_id = ? AND status IN ('queued', 'processing')", (batch_id,))
        rows = cursor.fetchall()
        for r in rows:
            jid = r["job_id"]
            cancel_job(jid)
            cancelled_count += 1
    return cancelled_count

def _sync_worker(job_id: str, input_path: str, output_path: str, preset_id: str, mode: str = "turbo", custom_overrides: Optional[dict] = None):
    # Check if cancelled before execution
    cur = JOBS_STORE.get(job_id)
    if cur and (str(cur.get("status")) in ["failed", "JobStatus.FAILED"] or "cancelled" in str(cur.get("message", "")).lower()):
        return

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
            progress_callback=on_progress,
            job_id=job_id
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
        # If cancelled, do not overwrite cancelled message
        cur = JOBS_STORE.get(job_id)
        if cur and "cancelled" in str(cur.get("message", "")).lower():
            return
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
    filename: Optional[str] = None,
    batch_id: Optional[str] = None
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
        "elapsed_seconds": None,
        "batch_id": batch_id
    }
    try:
        db_save_job(job_id, user_id, fn, preset_id, mode, status="queued", batch_id=batch_id)
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
    # Check if cancelled before execution
    cur = JOBS_STORE.get(job_id)
    if cur and (str(cur.get("status")) in ["failed", "JobStatus.FAILED"] or "cancelled" in str(cur.get("message", "")).lower()):
        return

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

        # Check again if cancelled during download
        cur = JOBS_STORE.get(job_id)
        if cur and "cancelled" in str(cur.get("message", "")).lower():
            return
        
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
            progress_callback=on_transform_progress,
            job_id=job_id
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
        cur = JOBS_STORE.get(job_id)
        if cur and "cancelled" in str(cur.get("message", "")).lower():
            return
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
    title: Optional[str] = None,
    batch_id: Optional[str] = None
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
        "elapsed_seconds": None,
        "batch_id": batch_id
    }
    try:
        db_save_job(job_id, user_id, fn, preset_id, mode, status="queued", batch_id=batch_id)
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

def submit_batch_youtube_jobs(
    batch_id: str,
    youtube_url: str,
    base_title: str,
    start_sec: float,
    end_sec: float,
    split_minutes: int,
    preset_id: str,
    mode: str = "turbo",
    custom_overrides: Optional[dict] = None,
    user_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Splits long video into sequential 5-15 minute chapters / parts.
    Enqueues them one-by-one into the serial queue for safe execution without OOM.
    """
    from api.config import INPUT_DIR, OUTPUT_DIR

    chunk_sec = float(split_minutes) * 60.0
    cur_start = max(0.0, float(start_sec))
    total_end = float(end_sec)

    clean_base = base_title or "Movie"
    if clean_base.lower().endswith(".mp4"):
        clean_base = clean_base[:-4]

    jobs = []
    part_num = 1

    while cur_start < total_end:
        cur_end = min(cur_start + chunk_sec, total_end)
        # Avoid tiny residual slice (e.g. less than 20 seconds) by merging with previous if small
        if (total_end - cur_end) < 20.0 and cur_end < total_end:
            cur_end = total_end

        job_id = str(uuid.uuid4())
        part_title = f"{clean_base} - Part {part_num}"
        input_path = os.path.join(INPUT_DIR, f"yt_{job_id}.mp4")
        output_path = os.path.join(OUTPUT_DIR, f"safe_{job_id}.mp4")

        submit_youtube_job(
            job_id=job_id,
            youtube_url=youtube_url,
            input_path=input_path,
            output_path=output_path,
            start_sec=cur_start,
            end_sec=cur_end,
            preset_id=preset_id,
            mode=mode,
            custom_overrides=custom_overrides,
            user_id=user_id,
            title=part_title,
            batch_id=batch_id
        )

        jobs.append({
            "job_id": job_id,
            "part_num": part_num,
            "title": part_title,
            "start_sec": cur_start,
            "end_sec": cur_end,
            "duration": cur_end - cur_start
        })

        part_num += 1
        cur_start = cur_end

    return jobs
