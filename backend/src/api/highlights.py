from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models import HighlightResponse, ApiResponse
from infrastructure.database import get_db
from infrastructure.repository import HighlightRepository

router = APIRouter()


@router.get("/{highlight_id}", response_model=HighlightResponse)
async def get_highlight(highlight_id: str, db: AsyncSession = Depends(get_db)):
    """하이라이트 상세 조회"""
    repo = HighlightRepository(db)
    highlight = await repo.get_by_id(highlight_id)

    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")

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
async def export_highlight(highlight_id: str, db: AsyncSession = Depends(get_db)):
    """하이라이트를 숏폼 영상으로 내보내기"""
    repo = HighlightRepository(db)
    highlight = await repo.get_by_id(highlight_id)

    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")

    # Mock 응답 - 실제 영상 처리는 추후 구현
    return ApiResponse(data={
        "success": True,
        "message": "Export job created",
        "export_id": f"export_{highlight_id}",
        "status": "processing",
        "estimated_time": 30,
    })


@router.delete("/{highlight_id}")
async def delete_highlight(highlight_id: str, db: AsyncSession = Depends(get_db)):
    """하이라이트 삭제"""
    repo = HighlightRepository(db)
    success = await repo.delete(highlight_id)

    if not success:
        raise HTTPException(status_code=404, detail="Highlight not found")

    return ApiResponse(data={"success": True, "message": "Highlight deleted"})
