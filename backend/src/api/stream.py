"""영상 파일 스트리밍 엔드포인트 (Range Request 지원)"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pathlib import Path
import os
import mimetypes

from core.config import get_settings

router = APIRouter()


@router.get("/videos/{video_id}/stream")
async def stream_video(video_id: int, request: Request):
    """
    영상 파일 스트리밍 (Range Request 지원)

    Response:
        200: 전체 파일 (Range 헤더 없을 때)
        206: 부분 콘텐츠 (Range 헤더 있을 때)
        404: 영상 파일 없음
    """
    video_path = _find_video_path(video_id)
    if not video_path:
        raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다")

    file_size = os.path.getsize(video_path)
    content_type = mimetypes.guess_type(video_path)[0] or "video/mp4"

    range_header = request.headers.get("range")

    if range_header:
        start, end = _parse_range(range_header, file_size)
        content_length = end - start + 1

        return StreamingResponse(
            _file_iterator(video_path, start, end),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            },
        )

    return StreamingResponse(
        _file_iterator(video_path, 0, file_size - 1),
        media_type=content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        },
    )


def _find_video_path(video_id: int) -> str | None:
    """영상 파일 경로 탐색"""
    upload_dir = Path(get_settings().upload_dir)

    # YouTube: {video_id}.mp4
    mp4_path = upload_dir / f"{video_id}.mp4"
    if mp4_path.exists():
        return str(mp4_path)

    # File upload: {video_id}_{filename} 패턴
    if upload_dir.exists():
        for f in upload_dir.iterdir():
            if f.name.startswith(f"{video_id}_") and f.is_file():
                return str(f)

    return None


def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    """Range 헤더 파싱 → (start, end)"""
    range_spec = range_header.replace("bytes=", "")
    parts = range_spec.split("-")
    start = int(parts[0]) if parts[0] else 0
    end = int(parts[1]) if parts[1] else file_size - 1
    end = min(end, file_size - 1)
    return start, end


async def _file_iterator(path: str, start: int, end: int, chunk_size: int = 1024 * 1024):
    """파일을 청크 단위로 스트리밍 (1MB 기본)"""
    with open(path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            remaining -= len(data)
            yield data
