from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobResponse(BaseModel):
    job_id: str
    filename: str
    status: JobStatus
    progress: float
    message: str
    preset: str
    download_url: Optional[str] = None
    original_meta: Optional[Dict[str, Any]] = None
    transformed_meta: Optional[Dict[str, Any]] = None
    elapsed_seconds: Optional[float] = None
    error: Optional[str] = None
    batch_id: Optional[str] = None
    parts_count: Optional[int] = None
