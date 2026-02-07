from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from models import VideoResponse, YouTubeURLRequest, ProcessingStatus, VideoSource
from services.video_processor import VideoProcessor
from datetime import datetime
import uuid

router = APIRouter()

# 임시 저장소 (실제로는 DB 사용)
videos_db: dict[str, dict] = {}
processor = VideoProcessor()


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """영상 파일 업로드 및 분석 시작"""

    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="영상 파일만 업로드 가능합니다")

    video_id = str(uuid.uuid4())

    video_data = {
        "id": video_id,
        "title": file.filename or "Untitled",
        "source": VideoSource(type="file", filename=file.filename),
        "duration": None,
        "status": ProcessingStatus.UPLOADING,
        "progress": 0,
        "message": "업로드 중...",
        "highlights": [],
        "created_at": datetime.now(),
    }

    videos_db[video_id] = video_data

    # 백그라운드에서 처리
    background_tasks.add_task(processor.process_file, video_id, file, videos_db)

    return VideoResponse(**video_data)


@router.post("/youtube", response_model=VideoResponse)
async def process_youtube(
    background_tasks: BackgroundTasks,
    request: YouTubeURLRequest
):
    """YouTube URL로 분석 시작"""

    video_id = str(uuid.uuid4())

    video_data = {
        "id": video_id,
        "title": "YouTube 영상",
        "source": VideoSource(type="youtube", url=request.url),
        "duration": None,
        "status": ProcessingStatus.PROCESSING,
        "progress": 0,
        "message": "YouTube 영상 정보 가져오는 중...",
        "highlights": [],
        "created_at": datetime.now(),
    }

    videos_db[video_id] = video_data

    # 백그라운드에서 처리
    background_tasks.add_task(processor.process_youtube, video_id, request.url, videos_db)

    return VideoResponse(**video_data)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str):
    """영상 정보 조회"""

    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다")

    return VideoResponse(**videos_db[video_id])


@router.get("/", response_model=list[VideoResponse])
async def list_videos():
    """모든 영상 목록 조회"""
    return [VideoResponse(**v) for v in videos_db.values()]


@router.delete("/{video_id}")
async def delete_video(video_id: str):
    """영상 삭제"""

    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="영상을 찾을 수 없습니다")

    del videos_db[video_id]
    return {"message": "삭제되었습니다"}
