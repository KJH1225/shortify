import asyncio
import os
from datetime import datetime
from pathlib import Path

from infrastructure.database import async_session_maker
from infrastructure.repository import VideoRepository, HighlightRepository
from models import ProcessingStatus
from core.config import get_settings
from core.constants import AI_PROCESSING_MESSAGES
from services.audio_extractor import AudioExtractor
from services.transcription_service import TranscriptionService
from services.highlight_analyzer import HighlightAnalyzer


class VideoProcessor:
    """영상 처리 서비스"""

    def __init__(self):
        self._download_progress: dict[int, int] = {}
        self._audio_extractor = AudioExtractor()
        self._transcription_service = TranscriptionService()
        self._highlight_analyzer = HighlightAnalyzer()

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

    def _download_youtube(self, url: str, output_path: str, video_id: int):
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

    def _on_download_progress(self, d: dict, video_id: int):
        """yt-dlp 다운로드 진행률 콜백 (동기 컨텍스트에서 실행)"""
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                self._download_progress[video_id] = int((downloaded / total) * 70) + 10

    async def process_file(self, video_id: int, file):
        """업로드된 파일 처리 - 디스크 저장 후 AI 분석"""
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

            # Step 4: AI 분석
            await self._analyze_video(video_id)

        except Exception as e:
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(video_id, ProcessingStatus.ERROR, 0, str(e))
                await db.commit()

    def _write_file(self, path: str, content: bytes):
        """파일 쓰기 (동기, asyncio.to_thread로 호출)"""
        with open(path, "wb") as f:
            f.write(content)

    async def process_youtube(self, video_id: int, url: str):
        """YouTube 영상 처리 - 실제 다운로드 후 AI 분석"""
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

            # Step 6: AI 분석
            await self._analyze_video(video_id)

        except Exception as e:
            self._download_progress.pop(video_id, None)
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(video_id, ProcessingStatus.ERROR, 0, str(e))
                await db.commit()

    async def _analyze_video(self, video_id: int):
        """실제 AI 분석 파이프라인 (실패 시 오류 응답)"""
        settings = get_settings()

        if not settings.has_openai_key():
            raise RuntimeError(
                "OpenAI API 키가 설정되지 않았습니다. "
                "환경변수 OPENAI_API_KEY를 설정해주세요."
            )

        # === Step 1: 오디오 추출 (10-20%) ===
        await self._update_progress(
            video_id, 10, AI_PROCESSING_MESSAGES["audio_extract_start"]
        )

        video_path = self._get_video_path(video_id)
        audio_path = self._get_audio_path(video_id)

        await self._audio_extractor.extract(video_path, audio_path)

        await self._update_progress(
            video_id, 20, AI_PROCESSING_MESSAGES["audio_extract_done"]
        )

        try:
            # === Step 2: STT (20-50%) ===
            await self._update_progress(
                video_id, 25, AI_PROCESSING_MESSAGES["stt_start"]
            )

            async def stt_progress_callback(msg: str):
                await self._update_progress(video_id, -1, msg)

            transcript = await self._transcription_service.transcribe(
                audio_path,
                on_progress=stt_progress_callback,
            )

            await self._update_progress(
                video_id, 50,
                AI_PROCESSING_MESSAGES["stt_done"].format(
                    segment_count=len(transcript.segments)
                ),
            )

            # === Step 3: 하이라이트 분석 (50-90%) ===
            await self._update_progress(
                video_id, 55, AI_PROCESSING_MESSAGES["analysis_start"]
            )

            duration = await self._get_video_duration(video_id)
            highlights = await self._highlight_analyzer.analyze(transcript, duration)

            await self._update_progress(
                video_id, 90,
                AI_PROCESSING_MESSAGES["analysis_done"].format(
                    count=len(highlights)
                ),
            )

            # === Step 4: DB 저장 (90-100%) ===
            await self._update_progress(
                video_id, 92, AI_PROCESSING_MESSAGES["saving"]
            )

            highlights_data = [
                {
                    "start_time": h.start_time,
                    "end_time": h.end_time,
                    "title": h.title,
                    "description": h.description,
                    "score": h.score,
                }
                for h in highlights
            ]

            async with async_session_maker() as db:
                highlight_repo = HighlightRepository(db)
                await highlight_repo.create_batch(video_id, highlights_data)
                await db.commit()

            # === 완료 ===
            async with async_session_maker() as db:
                repo = VideoRepository(db)
                await repo.update_status(
                    video_id, ProcessingStatus.COMPLETED, 100,
                    AI_PROCESSING_MESSAGES["completed"],
                )
                await db.commit()

        finally:
            # 임시 오디오 파일 정리
            self._cleanup_audio(audio_path)

    def _get_video_path(self, video_id: int) -> str:
        """영상 파일 경로 결정"""
        upload_dir = Path(get_settings().upload_dir)

        # YouTube: {video_id}.mp4
        mp4_path = upload_dir / f"{video_id}.mp4"
        if mp4_path.exists():
            return str(mp4_path)

        # File upload: {video_id}_{filename} 패턴 검색
        for f in upload_dir.iterdir():
            if f.name.startswith(f"{video_id}_") and f.is_file():
                return str(f)

        raise FileNotFoundError(
            f"영상 파일을 찾을 수 없습니다: video_id={video_id}"
        )

    def _get_audio_path(self, video_id: int) -> str:
        """오디오 출력 경로"""
        upload_dir = Path(get_settings().upload_dir)
        return str(upload_dir / "audio" / f"{video_id}.wav")

    async def _get_video_duration(self, video_id: int) -> float:
        """DB에서 영상 길이 조회"""
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            video = await repo.get_by_id(video_id)
            if video and video.duration:
                return video.duration
        return 600.0  # duration 없으면 기본값 10분

    async def _update_progress(self, video_id: int, progress: int, message: str):
        """DB 진행률 업데이트 (progress=-1이면 메시지만 변경)"""
        async with async_session_maker() as db:
            repo = VideoRepository(db)
            if progress >= 0:
                await repo.update_status(
                    video_id, ProcessingStatus.PROCESSING, progress, message
                )
            else:
                video = await repo.get_by_id(video_id)
                if video:
                    video.message = message
                    video.updated_at = datetime.now()
                    await db.flush()
            await db.commit()

    def _cleanup_audio(self, audio_path: str):
        """임시 오디오 파일 및 청크 삭제"""
        if os.path.exists(audio_path):
            os.remove(audio_path)

        # 청크 파일도 정리
        audio_dir = os.path.dirname(audio_path)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        if os.path.exists(audio_dir):
            for f in os.listdir(audio_dir):
                if f.startswith(f"{base_name}_chunk_"):
                    os.remove(os.path.join(audio_dir, f))
