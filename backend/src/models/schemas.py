from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    IDLE = "idle"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class VideoSource(BaseModel):
    type: str  # "file" | "youtube"
    url: str | None = None
    filename: str | None = None


class HighlightBase(BaseModel):
    start_time: float
    end_time: float
    title: str
    description: str | None = None
    score: float
    thumbnail_url: str | None = None


class HighlightCreate(HighlightBase):
    video_id: int


class HighlightResponse(HighlightBase):
    id: int
    video_id: int
    created_at: datetime


class VideoCreate(BaseModel):
    source: VideoSource


class VideoResponse(BaseModel):
    id: int
    title: str
    source: VideoSource
    duration: float | None
    status: ProcessingStatus
    progress: int
    message: str | None = None
    highlights: list[HighlightResponse]
    created_at: datetime
    updated_at: datetime


class YouTubeURLRequest(BaseModel):
    url: str


class ProcessingUpdate(BaseModel):
    status: ProcessingStatus
    progress: int
    message: str
