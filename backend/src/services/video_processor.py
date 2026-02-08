import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database import async_session_maker
from infrastructure.repository import VideoRepository, HighlightRepository
from models import ProcessingStatus
from core.constants import MOCK_HIGHLIGHTS_DATA, PROCESSING_MESSAGES


class VideoProcessor:
    """영상 처리 서비스 (Mock 구현)"""

    async def process_file(self, video_id: str, file):
        """업로드된 파일 처리"""
        try:
            async with async_session_maker() as db:
                repo = VideoRepository(db)

                # 업로드 시뮬레이션
                for progress in range(0, 31, 10):
                    await repo.update_status(video_id, ProcessingStatus.UPLOADING, progress, "영상 업로드 중...")
                    await db.commit()
                    await asyncio.sleep(0.3)

                await repo.update_status(video_id, ProcessingStatus.PROCESSING, 30, "분석 준비 중...")
                await db.commit()

            # 분석 시뮬레이션 (S1 세션 종료 후 독립 실행)
            await self._simulate_analysis(video_id)

        except Exception as e:
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(video_id, ProcessingStatus.ERROR, 0, str(e))
                await db.commit()

    async def process_youtube(self, video_id: str, url: str):
        """YouTube 영상 처리"""
        try:
            async with async_session_maker() as db:
                repo = VideoRepository(db)

                # YouTube 정보 가져오기 시뮬레이션
                await repo.update_status(video_id, ProcessingStatus.PROCESSING, 10, "YouTube 영상 정보 가져오는 중...")
                await db.commit()

            await asyncio.sleep(1)

            # 분석 시뮬레이션 (S1 세션 종료 후 독립 실행)
            await self._simulate_analysis(video_id)

        except Exception as e:
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(video_id, ProcessingStatus.ERROR, 0, str(e))
                await db.commit()

    async def _simulate_analysis(self, video_id: str):
        """AI 분석 시뮬레이션"""
        # Phase 1: 진행률 업데이트
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            for i, msg in enumerate(PROCESSING_MESSAGES):
                progress = 30 + (i * 15)
                await repo.update_status(video_id, ProcessingStatus.PROCESSING, progress, msg)
                await db.commit()
                await asyncio.sleep(0.8)

        # Phase 2: 하이라이트 생성 (독립 세션, 즉시 commit)
        async with async_session_maker() as db:
            highlight_repo = HighlightRepository(db)
            await highlight_repo.create_batch(video_id, MOCK_HIGHLIGHTS_DATA)
            await db.commit()

        # Phase 3: 최종 상태 업데이트 (독립 세션)
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            await repo.update_duration(video_id, 600.0)  # 10분
            await repo.update_status(video_id, ProcessingStatus.COMPLETED, 100, "분석이 완료되었습니다!")
            await db.commit()
