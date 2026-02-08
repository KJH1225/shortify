import asyncio
import os
from datetime import datetime
from pathlib import Path

from infrastructure.database import async_session_maker
from infrastructure.repository import VideoRepository, HighlightRepository
from models import ProcessingStatus
from core.config import get_settings
from core.constants import MOCK_HIGHLIGHTS_DATA, PROCESSING_MESSAGES


class VideoProcessor:
    """영상 처리 서비스"""

    def __init__(self):
        self._download_progress: dict[str, int] = {}

    def _check_ytdlp(self) -> bool:
        """yt-dlp 설치 여부 확인"""
        try:
            import yt_dlp  # noqa: F401
            return True
        except ImportError:
            return False

    def _extract_youtube_info(self, url: str) -> dict:
        """YouTube 메타정보 추출 (동기)"""
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", ""),
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
            }

    def _download_youtube(self, url: str, output_path: str, video_id: str):
        """YouTube 영상 다운로드 (동기, asyncio.to_thread로 호출)"""
        import yt_dlp

        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [
                lambda d: self._on_download_progress(d, video_id)
            ],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    def _on_download_progress(self, d: dict, video_id: str):
        """yt-dlp 다운로드 진행률 콜백 (동기 컨텍스트에서 실행)"""
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                self._download_progress[video_id] = int((downloaded / total) * 70) + 10

    async def process_file(self, video_id: str, file):
        """업로드된 파일 처리 - 디스크 저장 후 Mock 분석"""
        try:
            upload_dir = Path(get_settings().upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Step 1: 저장 시작 알림
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(
                    video_id, ProcessingStatus.UPLOADING, 10, "영상 저장 중..."
                )
                await db.commit()

            # Step 2: 파일 디스크 저장
            safe_filename = f"{video_id}_{file.filename}"
            file_path = upload_dir / safe_filename

            content = await file.read()
            await asyncio.to_thread(self._write_file, str(file_path), content)

            # Step 3: source_filename 업데이트
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                video = await repo.get_by_id(video_id)
                if video:
                    video.source_filename = safe_filename
                    video.updated_at = datetime.now()
                    await db.flush()
                await repo.update_status(
                    video_id, ProcessingStatus.PROCESSING, 30, "분석 준비 중..."
                )
                await db.commit()

            # Step 4: Mock 분석
            await self._simulate_analysis(video_id)

        except Exception as e:
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(video_id, ProcessingStatus.ERROR, 0, str(e))
                await db.commit()

    def _write_file(self, path: str, content: bytes):
        """파일 쓰기 (동기, asyncio.to_thread로 호출)"""
        with open(path, "wb") as f:
            f.write(content)

    async def process_youtube(self, video_id: str, url: str):
        """YouTube 영상 처리 - 실제 다운로드 후 Mock 분석"""
        try:
            # Step 1: yt-dlp 확인
            if not self._check_ytdlp():
                async with async_session_maker() as db:
                    repo = VideoRepository(db)
                    await repo.update_status(
                        video_id, ProcessingStatus.ERROR, 0,
                        "yt-dlp가 설치되지 않았습니다. pip install yt-dlp"
                    )
                    await db.commit()
                return

            # Step 2: 메타정보 추출
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(
                    video_id, ProcessingStatus.PROCESSING, 5,
                    "YouTube 영상 정보 가져오는 중..."
                )
                await db.commit()

            info = await asyncio.to_thread(self._extract_youtube_info, url)

            # Step 3: 메타정보 DB 반영
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                video = await repo.get_by_id(video_id)
                if video:
                    video.title = info.get("title", video.title)
                    video.duration = info.get("duration")
                    video.updated_at = datetime.now()
                    await db.flush()
                await repo.update_status(
                    video_id, ProcessingStatus.PROCESSING, 10,
                    "영상 다운로드 중..."
                )
                await db.commit()

            # Step 4: 영상 다운로드
            upload_dir = Path(get_settings().upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(upload_dir / f"{video_id}.mp4")

            await asyncio.to_thread(
                self._download_youtube, url, output_path, video_id
            )

            # 진행률 정리
            self._download_progress.pop(video_id, None)

            # Step 5: 다운로드 완료 확인
            if not os.path.exists(output_path):
                raise FileNotFoundError("YouTube 영상 다운로드에 실패했습니다")

            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(
                    video_id, ProcessingStatus.PROCESSING, 80,
                    "다운로드 완료, 분석 시작..."
                )
                await db.commit()

            # Step 6: Mock 분석
            await self._simulate_analysis(video_id)

        except Exception as e:
            self._download_progress.pop(video_id, None)
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(video_id, ProcessingStatus.ERROR, 0, str(e))
                await db.commit()

    async def _simulate_analysis(self, video_id: str):
        """AI 분석 시뮬레이션 (Mock - 추후 실제 AI로 교체)"""
        # Phase 1: 진행률 업데이트
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            for i, msg in enumerate(PROCESSING_MESSAGES):
                progress = 80 + (i * 3)  # 80~92 범위
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
            # duration이 아직 설정되지 않은 경우에만 Mock 값 사용
            video = await repo.get_by_id(video_id)
            if video and not video.duration:
                await repo.update_duration(video_id, 600.0)  # 10분 (Mock)
            await repo.update_status(video_id, ProcessingStatus.COMPLETED, 100, "분석이 완료되었습니다!")
            await db.commit()
