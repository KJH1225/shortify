"""Repository pattern for database operations"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from infrastructure.models import Video, Highlight
from models.schemas import VideoSource, ProcessingStatus, HighlightResponse
from datetime import datetime
from typing import List, Optional


class VideoRepository:
    """Repository for Video entity operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        title: str,
        source: VideoSource,
        status: ProcessingStatus = ProcessingStatus.IDLE,
    ) -> Video:
        """Create a new video record"""
        video = Video(
            title=title,
            source_type=source.type,
            source_url=source.url,
            source_filename=source.filename,
            status=status,
            progress=0,
            message="",
        )
        self.db.add(video)
        await self.db.flush()
        return video

    async def get_by_id(self, video_id: int) -> Optional[Video]:
        """Get video by ID with highlights"""
        result = await self.db.execute(
            select(Video)
            .options(selectinload(Video.highlights))
            .where(Video.id == video_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> List[Video]:
        """Get all videos with highlights"""
        result = await self.db.execute(
            select(Video)
            .options(selectinload(Video.highlights))
            .order_by(Video.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        video_id: int,
        status: ProcessingStatus,
        progress: int,
        message: str,
    ) -> Optional[Video]:
        """Update video processing status"""
        video = await self.get_by_id(video_id)
        if video:
            video.status = status
            video.progress = progress
            video.message = message
            video.updated_at = datetime.now()
            await self.db.flush()
        return video

    async def update_duration(self, video_id: int, duration: float) -> Optional[Video]:
        """Update video duration"""
        video = await self.get_by_id(video_id)
        if video:
            video.duration = duration
            video.updated_at = datetime.now()
            await self.db.flush()
        return video

    async def delete(self, video_id: int) -> bool:
        """Delete video and its highlights"""
        video = await self.get_by_id(video_id)
        if video:
            await self.db.delete(video)
            await self.db.flush()
            return True
        return False


class HighlightRepository:
    """Repository for Highlight entity operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_batch(
        self,
        video_id: int,
        highlights_data: List[dict],
    ) -> List[Highlight]:
        """Create multiple highlights for a video"""
        highlights = []
        for data in highlights_data:
            highlight = Highlight(
                video_id=video_id,
                start_time=data["start_time"],
                end_time=data["end_time"],
                title=data["title"],
                description=data["description"],
                score=data["score"],
                thumbnail_url=data.get("thumbnail_url"),
                clips=data.get("clips"),
            )
            self.db.add(highlight)
            highlights.append(highlight)

        await self.db.flush()
        return highlights

    async def get_by_video_id(self, video_id: int) -> List[Highlight]:
        """Get all highlights for a video"""
        result = await self.db.execute(
            select(Highlight)
            .where(Highlight.video_id == video_id)
            .order_by(Highlight.start_time)
        )
        return list(result.scalars().all())

    async def get_by_id(self, highlight_id: int) -> Optional[Highlight]:
        """Get highlight by ID"""
        result = await self.db.execute(
            select(Highlight).where(Highlight.id == highlight_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, highlight_id: int) -> bool:
        """Delete a highlight by ID"""
        highlight = await self.get_by_id(highlight_id)
        if highlight:
            await self.db.delete(highlight)
            await self.db.flush()
            return True
        return False

    async def delete_by_video_id(self, video_id: int) -> int:
        """Delete all highlights for a video"""
        highlights = await self.get_by_video_id(video_id)
        count = len(highlights)
        for highlight in highlights:
            await self.db.delete(highlight)
        await self.db.flush()
        return count


def video_to_dict(video: Video) -> dict:
    """Convert Video ORM model to dict for response"""
    return {
        "id": video.id,
        "title": video.title,
        "source": VideoSource(
            type=video.source_type,
            url=video.source_url,
            filename=video.source_filename,
        ),
        "duration": video.duration,
        "status": video.status,
        "progress": video.progress,
        "message": video.message or None,
        "highlights": [
            HighlightResponse(
                id=h.id,
                video_id=h.video_id,
                start_time=h.start_time,
                end_time=h.end_time,
                title=h.title,
                description=h.description,
                score=h.score,
                thumbnail_url=h.thumbnail_url,
                clips=h.clips,
                created_at=h.created_at,
            )
            for h in video.highlights
        ],
        "created_at": video.created_at,
        "updated_at": video.updated_at,
    }
