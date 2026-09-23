import os
import uuid
import json
import asyncio
import shutil
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Response, Header, Cookie, BackgroundTasks, Query
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles

from api.config import INPUT_DIR, OUTPUT_DIR, TEMP_DIR, ALLOWED_EXTENSIONS
from api.models import JobResponse, JobStatus
from core.presets import PRESETS
from core.youtube_service import get_youtube_info, get_downloader_info, download_media_file
from core.db import (
    create_user,
    authenticate_user,
    create_session,
    get_user_by_session,
    delete_session,
    db_get_user_jobs,
    is_registration_allowed
)
from workers.manager import (
    submit_job,
    submit_youtube_job,
    get_job_state,
    update_job_status,
    JOBS_STORE
)

router = APIRouter()

CHUNKS_BASE_DIR = os.path.join(TEMP_DIR, "chunks")
os.makedirs(CHUNKS_BASE_DIR, exist_ok=True)

def get_current_user_optional(
    authorization: Optional[str] = None,
    cr_session: Optional[str] = None
) -> Optional[dict]:
    token = None
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif isinstance(cr_session, str) and cr_session.strip():
        token = cr_session.strip()
    
    if token:
        return get_user_by_session(token)
    return None

# ================= AUTHENTICATION ENDPOINTS =================

@router.post("/auth/register")
async def api_register(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    try:
        user = create_user(username, password)
        token = create_session(user["id"])
        response.set_cookie(
            key="cr_session",
            value=token,
            max_age=30 * 86400,
            httponly=True,
            samesite="lax"
        )
        return {"status": "ok", "token": token, "user": user}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Registration error: " + str(e))

@router.post("/auth/login")
async def api_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(user["id"])
    response.set_cookie(
        key="cr_session",
        value=token,
        max_age=30 * 86400,
        httponly=True,
        samesite="lax"
    )
    return {"status": "ok", "token": token, "user": user}

@router.get("/auth/status")
async def api_auth_status():
    """Returns whether new user registration is open or locked for private single-user mode."""
    return {
        "status": "ok",
        "registration_allowed": is_registration_allowed()
    }

@router.get("/auth/me")
async def api_auth_me(
    authorization: Optional[str] = Header(None),
    cr_session: Optional[str] = Cookie(None)
):
    user = get_current_user_optional(authorization, cr_session)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}

@router.post("/auth/logout")
async def api_logout(
    response: Response,
    authorization: Optional[str] = Header(None),
    cr_session: Optional[str] = Cookie(None)
):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif cr_session:
        token = cr_session.strip()
    if token:
        delete_session(token)
    response.delete_cookie("cr_session")
    return {"status": "ok"}

# ================= USER PERSISTENT RENDERS =================

@router.get("/my-renders")
async def api_my_renders(
    authorization: Optional[str] = Header(None),
    cr_session: Optional[str] = Cookie(None)
):
    user = get_current_user_optional(authorization, cr_session)
    if not user:
        raise HTTPException(status_code=401, detail="Please login to view your cloud renders")
    jobs = db_get_user_jobs(user["id"])
    return {"status": "ok", "user": user, "jobs": jobs}

@router.delete("/my-renders/{job_id}")
async def api_delete_render(
    job_id: str,
    authorization: Optional[str] = Header(None),
    cr_session: Optional[str] = Cookie(None)
):
    user = get_current_user_optional(authorization, cr_session)
    user_id = user["id"] if user else None

    # 1. Purge physical files from storage
    for folder in [OUTPUT_DIR, INPUT_DIR, TEMP_DIR]:
        if not os.path.exists(folder): continue
        for f in os.listdir(folder):
            if job_id in f:
                try:
                    fpath = os.path.join(folder, f)
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                    elif os.path.isdir(fpath):
                        shutil.rmtree(fpath, ignore_errors=True)
                except Exception:
                    pass

    # 2. Purge from in-memory cache
    if job_id in JOBS_STORE:
        del JOBS_STORE[job_id]

    # 3. Purge from SQLite DB
    from core.db import db_delete_job
    db_delete_job(job_id, user_id)

    return {"status": "ok", "message": f"Job {job_id} and associated disk files permanently deleted"}

# ================= CORE ENGINE ENDPOINTS =================

@router.get("/presets")
async def get_presets():
    return list(PRESETS.values())

# 0. YouTube & Direct Video URL: Fetch Video Info (Title, Thumbnail, Duration)
@router.post("/youtube/info")
async def fetch_youtube_video_info(url: str = Form(...)):
    url = url.strip()
    is_yt = ("youtube.com" in url or "youtu.be" in url)
    is_direct = url.startswith(("http://", "https://")) and (
        url.split("?")[0].lower().endswith(('.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v')) or '/download' in url.lower() or 'cloud' in url.lower() or 'filesdl' in url.lower()
    )

    if not url or (not is_yt and not is_direct):
        raise HTTPException(status_code=400, detail="Please enter a valid YouTube video link or direct movie download URL")
    try:
        info = get_youtube_info(url)
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 0.1 YouTube: Auto-Find Viral Hooks (Studio 2)
@router.post("/youtube/find-hooks")
async def api_find_viral_hooks(url: str = Form(...)):
    if not url or ("youtube.com" not in url and "youtu.be" not in url):
        raise HTTPException(status_code=400, detail="Please enter a valid YouTube URL")
    try:
        from core.hook_finder import find_viral_hooks
        hooks = find_viral_hooks(url)
        return {"hooks": hooks, "count": len(hooks)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 0.2 Music & Lo-Fi Scrambler (Studio 3)
@router.post("/music/lofi", response_model=JobResponse)
async def api_process_lofi_music(
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    style: str = Form("slowed_reverb"),
    speed: float = Form(0.88),
    reverb_level: float = Form(0.5),
    authorization: Optional[str] = Header(None),
    cr_session: Optional[str] = Cookie(None)
):
    if not url and not file:
        raise HTTPException(status_code=400, detail="Please provide a YouTube song URL or upload an audio file")

    user = get_current_user_optional(authorization, cr_session)
    user_id = user["id"] if user else None

    is_youtube = bool(url and ("youtube.com" in url or "youtu.be" in url))
    
    job_id = str(uuid.uuid4())
    output_path = os.path.join(OUTPUT_DIR, f"safe_{job_id}.mp4")
    
    input_source = url
    filename = "Lo-Fi Track.mp3"
    if file:
        ext = os.path.splitext(file.filename)[1].lower() or ".mp3"
        local_input = os.path.join(INPUT_DIR, f"lofi_in_{job_id}{ext}")
        async with aiofiles.open(local_input, "wb") as f:
            while chunk := await file.read(1024 * 1024 * 2):
                await f.write(chunk)
        input_source = local_input
        filename = file.filename
        is_youtube = False

    # Save to memory and DB
    from core.db import db_save_job
    db_save_job(job_id, user_id, filename, "lofi_scrambler", "lofi", status="queued")

    JOBS_STORE[job_id] = {
        "job_id": job_id,
        "user_id": user_id,
        "filename": filename,
        "input_path": input_source or "Audio Track",
        "output_path": output_path,
        "preset": "lofi_scrambler",
        "mode": "lofi",
        "status": JobStatus.QUEUED,
        "progress": 0.0,
        "message": "Enqueued Lo-Fi audio scrambling pipeline...",
        "error": None,
        "download_url": None,
        "original_meta": None,
        "transformed_meta": None,
        "elapsed_seconds": None
    }

    # Background execution for Lo-Fi synthesis
    def run_lofi_task():
        from core.lofi_processor import process_music_lofi
        try:
            update_job_status(job_id, 20.0, "Generating Copyright-Free Lo-Fi / Slowed Track...", JobStatus.PROCESSING)

            process_music_lofi(
                input_source=input_source,
                output_path=output_path,
                is_youtube=is_youtube,
                style=style,
                speed=speed,
                reverb_level=reverb_level,
                progress_callback=lambda p, m: update_job_status(job_id, p, m, JobStatus.PROCESSING)
            )

            update_job_status(
                job_id=job_id,
                progress=100.0,
                message="Copyright-Free Lo-Fi Track Ready!",
                status=JobStatus.COMPLETED,
                download_url=f"/api/download/{job_id}"
            )
        except Exception as err:
            update_job_status(
                job_id=job_id,
                progress=0.0,
                message=f"Lo-Fi generation failed: {str(err)}",
                status=JobStatus.FAILED,
                error=str(err)
            )

    import threading
    threading.Thread(target=run_lofi_task, daemon=True).start()

    return JobResponse(
        job_id=job_id,
        filename=filename,
        status=JobStatus.QUEUED,
        progress=0.0,
        message="Enqueued Lo-Fi music transformation pipeline...",
        preset="lofi_scrambler"
    )

# 0.5 YouTube & Direct Video: Process Trimmed Video to Copyright-Free
@router.post("/youtube/process", response_model=JobResponse)
async def process_youtube_video(
    url: str = Form(...),
    start_sec: float = Form(0.0),
    end_sec: Optional[float] = Form(None),
    preset: str = Form("stealth_deep"),
    mode: str = Form("turbo"),
    custom_settings: Optional[str] = Form(None),
    video_title: Optional[str] = Form(None),
    split_minutes: int = Form(0),
    authorization: Optional[str] = Header(None),
    cr_session: Optional[str] = Cookie(None)
):
    url = url.strip()
    is_yt = ("youtube.com" in url or "youtu.be" in url)
    is_direct = url.startswith(("http://", "https://")) and (
        url.split("?")[0].lower().endswith(('.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v')) or '/download' in url.lower() or 'cloud' in url.lower() or 'filesdl' in url.lower()
    )

    if not url or (not is_yt and not is_direct):
        raise HTTPException(status_code=400, detail="Invalid video URL")

    user = get_current_user_optional(authorization, cr_session)
    user_id = user["id"] if user else None

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

    display_title = video_title or f"Stream_{uuid.uuid4().hex[:6]}.mp4"

    # Multi-Part Batch Auto-Splitter
    if split_minutes and split_minutes > 0 and end_sec and (float(end_sec) - float(start_sec)) > (float(split_minutes) * 60.0):
        from workers.manager import submit_batch_youtube_jobs
        batch_id = str(uuid.uuid4())
        jobs = submit_batch_youtube_jobs(
            batch_id=batch_id,
            youtube_url=url,
            base_title=display_title,
            start_sec=float(start_sec),
            end_sec=float(end_sec),
            split_minutes=int(split_minutes),
            preset_id=preset,
            mode=mode,
            custom_overrides=custom_overrides,
            user_id=user_id
        )
        first_job = jobs[0]
        return JobResponse(
            job_id=first_job["job_id"],
            filename=first_job["title"],
            status=JobStatus.QUEUED,
            progress=0.0,
            message=f"Enqueued {len(jobs)} parts into background pipeline! Part 1 is starting...",
            preset=preset,
            batch_id=batch_id,
            parts_count=len(jobs)
        )

    job_id = str(uuid.uuid4())
    input_path = os.path.join(INPUT_DIR, f"yt_{job_id}.mp4")
    output_path = os.path.join(OUTPUT_DIR, f"safe_{job_id}.mp4")

    submit_youtube_job(
        job_id=job_id,
        youtube_url=url,
        input_path=input_path,
        output_path=output_path,
        start_sec=start_sec,
        end_sec=end_sec,
        preset_id=preset,
        mode=mode,
        custom_overrides=custom_overrides,
        user_id=user_id,
        title=display_title
    )

    return JobResponse(
        job_id=job_id,
        filename=display_title,
        status=JobStatus.QUEUED,
        progress=0.0,
        message="Connecting to stream & queuing transformation...",
        preset=preset
    )

# 0.6 Cancellation Endpoints
@router.post("/jobs/{job_id}/cancel")
async def api_cancel_job(job_id: str):
    from workers.manager import cancel_job
    success = cancel_job(job_id)
    return {"status": "ok", "cancelled": success, "message": f"Job {job_id} cancelled successfully"}

@router.post("/batches/{batch_id}/cancel")
async def api_cancel_batch(batch_id: str):
    from workers.manager import cancel_batch
    count = cancel_batch(batch_id)
    return {"status": "ok", "cancelled_count": count, "message": f"{count} parts in batch cancelled"}

# 1. Chunked Upload: Initialize
@router.post("/upload/init")
async def init_chunked_upload(
    filename: str = Form(...),
    total_chunks: int = Form(...),
    file_size: int = Form(...)
):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    upload_id = str(uuid.uuid4())
    upload_dir = os.path.join(CHUNKS_BASE_DIR, upload_id)
    os.makedirs(upload_dir, exist_ok=True)
    return {
        "upload_id": upload_id,
        "filename": filename,
        "total_chunks": total_chunks
    }

# 2. Chunked Upload: Receive 1-2MB slice
@router.post("/upload/chunk")
async def receive_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...)
):
    upload_dir = os.path.join(CHUNKS_BASE_DIR, upload_id)
    if not os.path.exists(upload_dir):
        raise HTTPException(status_code=404, detail="Upload session expired or invalid")
        
    chunk_path = os.path.join(upload_dir, f"{chunk_index:06d}.part")
    content = await chunk.read()
    async with aiofiles.open(chunk_path, "wb") as f:
        await f.write(content)
        
    return {"status": "ok", "chunk_index": chunk_index}

# 3. Chunked Upload: Assemble and Start Processing
@router.post("/upload/complete", response_model=JobResponse)
async def complete_chunked_upload(
    upload_id: str = Form(...),
    filename: str = Form(...),
    preset: str = Form("stealth_deep"),
    mode: str = Form("turbo"),
    custom_settings: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    cr_session: Optional[str] = Cookie(None)
):
    upload_dir = os.path.join(CHUNKS_BASE_DIR, upload_id)
    if not os.path.exists(upload_dir):
        raise HTTPException(status_code=404, detail="Upload session not found")

    user = get_current_user_optional(authorization, cr_session)
    user_id = user["id"] if user else None

    ext = os.path.splitext(filename)[1].lower()
    job_id = upload_id
    safe_name = f"{job_id}{ext}"
    final_input_path = os.path.join(INPUT_DIR, safe_name)
    final_output_path = os.path.join(OUTPUT_DIR, f"safe_{job_id}.mp4")

    # Assemble all chunks in numerical order
    chunk_files = sorted(os.listdir(upload_dir))
    if not chunk_files:
        raise HTTPException(status_code=400, detail="No chunks received")

    with open(final_input_path, "wb") as out_f:
        for cf in chunk_files:
            part_path = os.path.join(upload_dir, cf)
            with open(part_path, "rb") as in_f:
                shutil.copyfileobj(in_f, out_f, length=1024*1024)

    # Clean up chunks folder
    shutil.rmtree(upload_dir, ignore_errors=True)

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

    submit_job(
        job_id=job_id,
        input_path=final_input_path,
        output_path=final_output_path,
        preset_id=preset,
        mode=mode,
        custom_overrides=custom_overrides,
        user_id=user_id,
        filename=filename
    )

    return JobResponse(
        job_id=job_id,
        filename=filename,
        status=JobStatus.QUEUED,
        progress=0.0,
        message="Video assembled successfully! Enqueued in transformation pipeline.",
        preset=preset
    )

# 4. Standard Direct Upload (Fallback)
@router.post("/upload", response_model=JobResponse)
async def upload_video(
    file: UploadFile = File(...),
    preset: str = Form("stealth_deep"),
    mode: str = Form("turbo"),
    custom_settings: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    cr_session: Optional[str] = Cookie(None)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    user = get_current_user_optional(authorization, cr_session)
    user_id = user["id"] if user else None

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
    
    async with aiofiles.open(input_path, "wb") as f:
        while chunk := await file.read(1024 * 1024 * 2): # 2MB chunks
            await f.write(chunk)
            
    submit_job(
        job_id=job_id,
        input_path=input_path,
        output_path=output_path,
        preset_id=preset,
        mode=mode,
        custom_overrides=custom_overrides,
        user_id=user_id,
        filename=file.filename
    )
    
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
    job = get_job_state(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return JobResponse(
        job_id=job_id,
        filename=job.get("filename", os.path.basename(job.get("input_path", "video.mp4"))),
        status=job["status"] if isinstance(job["status"], JobStatus) else JobStatus(job["status"]),
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
    job = get_job_state(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        while True:
            cur = get_job_state(job_id)
            if not cur:
                break
            
            st_val = cur["status"].value if hasattr(cur["status"], "value") else str(cur["status"])
            data = json.dumps({
                "status": st_val,
                "progress": cur["progress"],
                "message": cur["message"],
                "download_url": cur.get("download_url"),
                "elapsed": cur.get("elapsed_seconds")
            })
            yield f"data: {data}\n\n"
            
            if st_val in ["completed", "failed"]:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

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
        "active_jobs": len([j for j in JOBS_STORE.values() if str(j.get("status")) in ["processing", "JobStatus.PROCESSING"]]),
        "storage": {
            "free_gb": round(free / (1024**3), 2),
            "total_gb": round(total / (1024**3), 2)
        }
    }

# ================= VIDEO DOWNLOADER TAB ENDPOINTS =================

@router.post("/downloader/info")
async def api_downloader_info(url: str = Form(...)):
    """Fetches video metadata & available resolution formats for direct download."""
    clean_url = url.strip()
    if not clean_url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    try:
        data = await asyncio.to_thread(get_downloader_info, clean_url)
        return {"status": "ok", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch video: {str(e)}")

@router.get("/downloader/download")
async def api_downloader_download(
    background_tasks: BackgroundTasks,
    url: str = Query(...),
    quality: str = Query("720p")
):
    """
    Downloads raw YouTube video or direct CDN file in requested quality and streams it directly to device.
    Auto-cleans the temporary file from disk once download completes.
    """
    clean_url = url.strip()
    if not clean_url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
        
    dl_id = str(uuid.uuid4())
    ext = "mp3" if quality == "mp3" else "mp4"
    temp_target = os.path.join(TEMP_DIR, f"dl_{dl_id}.{ext}")

    def _cleanup(file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

    try:
        actual_path = await asyncio.to_thread(download_media_file, clean_url, quality, temp_target)
        if not os.path.exists(actual_path):
            raise HTTPException(status_code=500, detail="Downloaded media file could not be found.")

        # Determine clean user-facing filename
        actual_ext = os.path.splitext(actual_path)[1] or f".{ext}"
        user_filename = f"video_{quality}_{dl_id[:6]}{actual_ext}" if quality != "mp3" else f"audio_{dl_id[:6]}.mp3"

        background_tasks.add_task(_cleanup, actual_path)

        media_type = "audio/mpeg" if actual_ext == ".mp3" else "video/mp4"
        return FileResponse(
            path=actual_path,
            filename=user_filename,
            media_type=media_type,
            background=background_tasks
        )
    except Exception as e:
        _cleanup(temp_target)
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

