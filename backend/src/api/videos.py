import re
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from models import VideoResponse, YouTubeURLRequest, ProcessingStatus, VideoSource
from services.video_processor import VideoProcessor
from datetime import datetime
import uuid

router = APIRouter()

# 임시 저장소 (실제로는 DB 사용)
videos_db: dict[str, dict] = {}
processor = VideoProcessor()

# 파일 검증 설정
ALLOWED_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
ALLOWED_MIME_TYPES = {
    'video/mp4', 'video/quicktime', 'video/x-msvideo',
    'video/x-matroska', 'video/webm', 'video/x-m4v'
}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

# YouTube URL 패턴
YOUTUBE_URL_PATTERNS = [
    r'^https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
    r'^https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    r'^https?://(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
    r'^https?://youtu\.be/([a-zA-Z0-9_-]{11})',
    r'^https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
]


def validate_youtube_url(url: str) -> str | None:
    """YouTube URL 검증 및 비디오 ID 추출"""
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    return None


def validate_file_extension(filename: str) -> bool:
    """파일 확장자 검증"""
    if not filename:
        return False
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """영상 파일 업로드 및 분석 시작"""

    # MIME 타입 검증
    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 파일 확장자 검증
    if not validate_file_extension(file.filename or ''):
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 확장자입니다. 지원 형식: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 파일 크기 검증 (Content-Length 헤더 기반)
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 너무 큽니다. 최대 {MAX_FILE_SIZE // (1024*1024*1024)}GB까지 업로드 가능합니다."
        )

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

    # YouTube URL 검증
    video_id_yt = validate_youtube_url(request.url)
    if not video_id_yt:
        raise HTTPException(
            status_code=400,
            detail="유효한 YouTube URL이 아닙니다. YouTube 영상 URL을 입력해주세요."
        )

    video_id = str(uuid.uuid4())

    video_data = {
        "id": video_id,
        "title": f"YouTube: {video_id_yt}",
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
