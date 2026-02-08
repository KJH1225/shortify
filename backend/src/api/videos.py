import re
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models import VideoResponse, YouTubeURLRequest, ProcessingStatus, VideoSource, ApiResponse, ApiError
from services.video_processor import VideoProcessor
from infrastructure.database import get_db
from infrastructure.repository import VideoRepository, video_to_dict
from core.constants import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
    YOUTUBE_URL_PATTERNS,
)

router = APIRouter()
processor = VideoProcessor()


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
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """영상 파일 업로드 및 분석 시작"""

    # MIME 타입 검증
    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                code="INVALID_MIME_TYPE",
                message="지원하지 않는 파일 형식입니다",
                details={"supported_types": list(ALLOWED_EXTENSIONS)}
            ).model_dump()
        )

    # 파일 확장자 검증
    if not validate_file_extension(file.filename or ''):
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                code="INVALID_FILE_EXTENSION",
                message="지원하지 않는 파일 확장자입니다",
                details={"supported_extensions": list(ALLOWED_EXTENSIONS)}
            ).model_dump()
        )

    # 파일 크기 검증 (Content-Length 헤더 기반)
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                code="FILE_TOO_LARGE",
                message="파일 크기가 너무 큽니다",
                details={"max_size_gb": MAX_FILE_SIZE // (1024*1024*1024)}
            ).model_dump()
        )

    repo = VideoRepository(db)

    # DB에 비디오 레코드 생성
    video = await repo.create(
        title=file.filename or "Untitled",
        source=VideoSource(type="file", filename=file.filename),
        status=ProcessingStatus.UPLOADING,
    )
    await repo.update_status(video.id, ProcessingStatus.UPLOADING, 0, "업로드 중...")
    await db.commit()

    # 백그라운드에서 처리
    background_tasks.add_task(processor.process_file, video.id, file)

    return VideoResponse(**video_to_dict(video))


@router.post("/youtube", response_model=VideoResponse)
async def process_youtube(
    background_tasks: BackgroundTasks,
    request: YouTubeURLRequest,
    db: AsyncSession = Depends(get_db),
):
    """YouTube URL로 분석 시작"""

    # YouTube URL 검증
    video_id_yt = validate_youtube_url(request.url)
    if not video_id_yt:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                code="INVALID_YOUTUBE_URL",
                message="유효한 YouTube URL이 아닙니다",
                details={"provided_url": request.url}
            ).model_dump()
        )

    repo = VideoRepository(db)

    # DB에 비디오 레코드 생성
    video = await repo.create(
        title=f"YouTube: {video_id_yt}",
        source=VideoSource(type="youtube", url=request.url),
        status=ProcessingStatus.PROCESSING,
    )
    await repo.update_status(video.id, ProcessingStatus.PROCESSING, 0, "YouTube 영상 정보 가져오는 중...")
    await db.commit()

    # 백그라운드에서 처리
    background_tasks.add_task(processor.process_youtube, video.id, request.url)

    return VideoResponse(**video_to_dict(video))


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """영상 정보 조회"""
    repo = VideoRepository(db)
    video = await repo.get_by_id(video_id)

    if not video:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="VIDEO_NOT_FOUND",
                message="영상을 찾을 수 없습니다",
                details={"video_id": video_id}
            ).model_dump()
        )

    return VideoResponse(**video_to_dict(video))


@router.get("/", response_model=list[VideoResponse])
async def list_videos(db: AsyncSession = Depends(get_db)):
    """모든 영상 목록 조회"""
    repo = VideoRepository(db)
    videos = await repo.list_all()
    return [VideoResponse(**video_to_dict(v)) for v in videos]


@router.delete("/{video_id}")
async def delete_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """영상 삭제"""
    repo = VideoRepository(db)
    deleted = await repo.delete(video_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="VIDEO_NOT_FOUND",
                message="영상을 찾을 수 없습니다",
                details={"video_id": video_id}
            ).model_dump()
        )

    return ApiResponse(data={"success": True, "message": "삭제되었습니다"})
