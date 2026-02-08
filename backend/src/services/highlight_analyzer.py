"""GPT-4o-mini 기반 하이라이트 분석 서비스"""
import asyncio
import json
from dataclasses import dataclass

from openai import AsyncOpenAI

from core.config import get_settings
from core.constants import HIGHLIGHT_SYSTEM_PROMPT, HIGHLIGHT_USER_PROMPT
from services.transcription_service import TranscriptionResult


@dataclass
class HighlightResult:
    """AI가 추출한 하이라이트"""
    start_time: float
    end_time: float
    title: str
    description: str
    score: float


class HighlightAnalyzer:
    """GPT-4o-mini 기반 하이라이트 분석 서비스"""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_chat_model
        self.max_highlights = settings.max_highlights
        self.retry_count = settings.ai_retry_count
        self.retry_delay = settings.ai_retry_delay

    async def analyze(
        self,
        transcript: TranscriptionResult,
        duration: float,
    ) -> list[HighlightResult]:
        """
        트랜스크립트를 분석하여 하이라이트 추출

        Args:
            transcript: STT 결과
            duration: 영상 전체 길이 (초)

        Returns:
            하이라이트 목록 (score 내림차순)

        Raises:
            RuntimeError: GPT API 호출 또는 파싱 실패
        """
        if not transcript.full_text.strip():
            raise RuntimeError("트랜스크립트가 비어있어 하이라이트를 추출할 수 없습니다")

        formatted_transcript = self._build_transcript_text(transcript)
        target_count = self._calculate_target_count(duration)

        for attempt in range(self.retry_count):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": HIGHLIGHT_SYSTEM_PROMPT},
                        {"role": "user", "content": HIGHLIGHT_USER_PROMPT.format(
                            duration=duration,
                            target_count=target_count,
                            transcript=formatted_transcript,
                        )},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=2000,
                )

                content = response.choices[0].message.content
                highlights = self._parse_response(content)
                validated = self._validate_highlights(highlights, duration)

                if not validated:
                    raise RuntimeError("유효한 하이라이트를 추출하지 못했습니다")

                return sorted(validated, key=lambda h: h.score, reverse=True)

            except RuntimeError:
                if attempt == self.retry_count - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
            except Exception as e:
                if attempt == self.retry_count - 1:
                    raise RuntimeError(f"하이라이트 분석 실패: {e}") from e
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

    def _build_transcript_text(self, transcript: TranscriptionResult) -> str:
        """세그먼트를 타임스탬프 포함 텍스트로 포맷"""
        lines = []
        for seg in transcript.segments:
            minutes = int(seg.start // 60)
            seconds = int(seg.start % 60)
            lines.append(f"[{minutes:02d}:{seconds:02d}] {seg.text}")
        return "\n".join(lines)

    def _calculate_target_count(self, duration: float) -> int:
        """영상 길이에 비례한 목표 하이라이트 수"""
        minutes = duration / 60
        return max(1, min(int(minutes), self.max_highlights))

    def _parse_response(self, content: str) -> list[HighlightResult]:
        """GPT 응답 JSON 파싱"""
        data = json.loads(content)

        # {"highlights": [...]} 또는 직접 [...] 지원
        if isinstance(data, dict) and "highlights" in data:
            items = data["highlights"]
        elif isinstance(data, list):
            items = data
        else:
            raise RuntimeError(f"예상치 못한 응답 형식: {type(data)}")

        highlights = []
        for item in items:
            highlights.append(HighlightResult(
                start_time=float(item["start_time"]),
                end_time=float(item["end_time"]),
                title=str(item["title"])[:20],
                description=str(item.get("description", ""))[:50],
                score=float(item.get("score", 0.5)),
            ))

        return highlights

    def _validate_highlights(
        self,
        highlights: list[HighlightResult],
        duration: float,
    ) -> list[HighlightResult]:
        """하이라이트 유효성 검증"""
        validated = []

        for h in highlights:
            # 시간 범위 클램핑
            h.start_time = max(0.0, h.start_time)
            h.end_time = min(duration, h.end_time)

            # 역전 제거
            if h.end_time <= h.start_time:
                continue

            # 길이 조정 (15~60초)
            length = h.end_time - h.start_time
            if length < 15:
                h.end_time = min(h.start_time + 15, duration)
            elif length > 60:
                h.end_time = h.start_time + 60

            # score 클램핑
            h.score = max(0.0, min(1.0, h.score))

            validated.append(h)

        # 겹침 제거 (score 높은 것 우선)
        validated.sort(key=lambda x: x.score, reverse=True)
        non_overlapping = []
        for h in validated:
            overlap = False
            for existing in non_overlapping:
                if h.start_time < existing.end_time and h.end_time > existing.start_time:
                    overlap = True
                    break
            if not overlap:
                non_overlapping.append(h)

        return non_overlapping[:self.max_highlights]
