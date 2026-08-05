from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobStatusResponse(BaseModel):
    id: str
    filename: str
    status: str
    file_size_mb: Optional[float]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

class JobListResponse(BaseModel):
    jobs: list[JobStatusResponse]
    total: int
