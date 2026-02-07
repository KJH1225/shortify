from fastapi import APIRouter, HTTPException
from models import HighlightResponse

router = APIRouter()


@router.get("/{highlight_id}", response_model=HighlightResponse)
async def get_highlight(highlight_id: str):
    """하이라이트 상세 조회"""
    raise HTTPException(status_code=501, detail="아직 구현되지 않았습니다")


@router.post("/{highlight_id}/export")
async def export_highlight(highlight_id: str):
    """하이라이트를 숏폼 영상으로 내보내기"""
    raise HTTPException(status_code=501, detail="아직 구현되지 않았습니다")


@router.delete("/{highlight_id}")
async def delete_highlight(highlight_id: str):
    """하이라이트 삭제"""
    raise HTTPException(status_code=501, detail="아직 구현되지 않았습니다")
