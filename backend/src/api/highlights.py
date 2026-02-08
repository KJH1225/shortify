from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from models import HighlightResponse, ApiResponse, ApiError
from infrastructure.database import get_db
from infrastructure.repository import HighlightRepository, VideoRepository
from services.export_processor import export_processor
from core.config import get_settings
from pathlib import Path

router = APIRouter()


@router.get("/{highlight_id}", response_model=HighlightResponse)
async def get_highlight(highlight_id: str, db: AsyncSession = Depends(get_db)):
    """하이라이트 상세 조회"""
    repo = HighlightRepository(db)
    highlight = await repo.get_by_id(highlight_id)

    if not highlight:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="HIGHLIGHT_NOT_FOUND",
                message="하이라이트를 찾을 수 없습니다",
                details={"highlight_id": highlight_id}
            ).model_dump()
        )

    return HighlightResponse(
        id=highlight.id,
        video_id=highlight.video_id,
        start_time=highlight.start_time,
        end_time=highlight.end_time,
        title=highlight.title,
        description=highlight.description,
        score=highlight.score,
        thumbnail_url=highlight.thumbnail_url,
        created_at=highlight.created_at,
    )


@router.post("/{highlight_id}/export")
async def export_highlight(
    highlight_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """하이라이트를 숏폼 영상으로 내보내기 (FFmpeg 사용)"""
    highlight_repo = HighlightRepository(db)
    highlight = await highlight_repo.get_by_id(highlight_id)

    if not highlight:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="HIGHLIGHT_NOT_FOUND",
                message="하이라이트를 찾을 수 없습니다",
                details={"highlight_id": highlight_id}
            ).model_dump()
        )

    # Get video info for source path
    video_repo = VideoRepository(db)
    video = await video_repo.get_by_id(highlight.video_id)

    if not video:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="VIDEO_NOT_FOUND",
                message="원본 영상을 찾을 수 없습니다",
                details={"video_id": highlight.video_id}
            ).model_dump()
        )

    # Determine video source path
    video_path = None
    if video.source_type == "file" and video.source_filename:
        video_path = str(Path(get_settings().upload_dir) / video.source_filename)
    elif video.source_type == "youtube" and video.source_url:
        # For YouTube videos, we need to download first (simplified path)
        video_path = str(Path(get_settings().upload_dir) / f"{video.id}.mp4")

    # Create export job
    job = await export_processor.create_export_job(
        highlight_id=highlight_id,
        video_path=video_path or "",
        start_time=highlight.start_time,
        end_time=highlight.end_time,
    )

    # Calculate estimated time (rough estimate based on duration)
    duration = highlight.end_time - highlight.start_time
    estimated_time = max(10, int(duration * 0.5))  # ~0.5x realtime for encoding

    # Process in background
    background_tasks.add_task(export_processor.process_export, job)

    return ApiResponse(data={
        "success": True,
        "message": "Export job created",
        "export_id": job.export_id,
        "status": job.status.value,
        "estimated_time": estimated_time,
        "highlight": {
            "id": highlight.id,
            "title": highlight.title,
            "start_time": highlight.start_time,
            "end_time": highlight.end_time,
            "duration": duration,
        }
    })


@router.get("/{highlight_id}/export/{export_id}/status")
async def get_export_status(highlight_id: str, export_id: str):
    """Export 작업 상태 조회"""
    job_status = export_processor.get_job_status(export_id)

    if "error" in job_status:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="EXPORT_JOB_NOT_FOUND",
                message="Export 작업을 찾을 수 없습니다",
                details={"export_id": export_id}
            ).model_dump()
        )

    return ApiResponse(data=job_status)


@router.delete("/{highlight_id}")
async def delete_highlight(highlight_id: str, db: AsyncSession = Depends(get_db)):
    """하이라이트 삭제"""
    repo = HighlightRepository(db)
    success = await repo.delete(highlight_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="HIGHLIGHT_NOT_FOUND",
                message="하이라이트를 찾을 수 없습니다",
                details={"highlight_id": highlight_id}
            ).model_dump()
        )

    return ApiResponse(data={"success": True, "message": "Highlight deleted"})
