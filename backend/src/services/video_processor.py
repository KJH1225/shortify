import asyncio
from datetime import datetime
import uuid
from models import ProcessingStatus, HighlightResponse


class VideoProcessor:
    """영상 처리 서비스 (Mock 구현)"""

    async def process_file(self, video_id: str, file, videos_db: dict):
        """업로드된 파일 처리"""
        try:
            # 업로드 시뮬레이션
            for progress in range(0, 31, 10):
                videos_db[video_id]["progress"] = progress
                videos_db[video_id]["message"] = "영상 업로드 중..."
                await asyncio.sleep(0.3)

            videos_db[video_id]["status"] = ProcessingStatus.PROCESSING

            # 분석 시뮬레이션
            await self._simulate_analysis(video_id, videos_db)

        except Exception as e:
            videos_db[video_id]["status"] = ProcessingStatus.ERROR
            videos_db[video_id]["message"] = str(e)

    async def process_youtube(self, video_id: str, url: str, videos_db: dict):
        """YouTube 영상 처리"""
        try:
            # YouTube 정보 가져오기 시뮬레이션
            videos_db[video_id]["progress"] = 10
            videos_db[video_id]["message"] = "YouTube 영상 정보 가져오는 중..."
            await asyncio.sleep(1)

            videos_db[video_id]["title"] = f"YouTube: {url.split('=')[-1][:8]}..."

            # 분석 시뮬레이션
            await self._simulate_analysis(video_id, videos_db)

        except Exception as e:
            videos_db[video_id]["status"] = ProcessingStatus.ERROR
            videos_db[video_id]["message"] = str(e)

    async def _simulate_analysis(self, video_id: str, videos_db: dict):
        """AI 분석 시뮬레이션"""
        messages = [
            "오디오 트랙 추출 중...",
            "음성을 텍스트로 변환 중...",
            "감정 분석 진행 중...",
            "하이라이트 구간 탐지 중...",
            "최적의 클립 선택 중...",
        ]

        for i, msg in enumerate(messages):
            progress = 30 + (i * 15)
            videos_db[video_id]["progress"] = progress
            videos_db[video_id]["message"] = msg
            await asyncio.sleep(0.8)

        # 하이라이트 생성
        highlights = self._generate_mock_highlights(video_id)
        videos_db[video_id]["highlights"] = highlights
        videos_db[video_id]["duration"] = 600.0  # 10분
        videos_db[video_id]["status"] = ProcessingStatus.COMPLETED
        videos_db[video_id]["progress"] = 100
        videos_db[video_id]["message"] = "분석이 완료되었습니다!"

    def _generate_mock_highlights(self, video_id: str) -> list[HighlightResponse]:
        """Mock 하이라이트 데이터 생성"""
        mock_data = [
            {"start": 45, "end": 78, "title": "핵심 개념 설명", "desc": "영상에서 가장 중요한 핵심 개념을 설명하는 구간입니다.", "score": 0.95},
            {"start": 120, "end": 165, "title": "놀라운 반전", "desc": "시청자들의 반응이 가장 뜨거웠던 반전 구간입니다.", "score": 0.92},
            {"start": 210, "end": 245, "title": "실용적인 팁", "desc": "바로 적용할 수 있는 실용적인 팁을 공유하는 구간입니다.", "score": 0.88},
            {"start": 300, "end": 340, "title": "감동적인 순간", "desc": "영상에서 가장 감동적인 순간이 담긴 구간입니다.", "score": 0.85},
            {"start": 420, "end": 480, "title": "결론 및 요약", "desc": "전체 내용을 깔끔하게 정리하는 마무리 구간입니다.", "score": 0.82},
        ]

        return [
            HighlightResponse(
                id=str(uuid.uuid4()),
                video_id=video_id,
                start_time=h["start"],
                end_time=h["end"],
                title=h["title"],
                description=h["desc"],
                score=h["score"],
                thumbnail_url=None,
                created_at=datetime.now(),
            )
            for h in mock_data
        ]
