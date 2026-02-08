"""OpenAI Whisper API 기반 음성-텍스트 변환 서비스"""
import asyncio
import os
from dataclasses import dataclass, field
from typing import Callable, Awaitable

from openai import AsyncOpenAI

from core.config import get_settings
from core.constants import AI_PROCESSING_MESSAGES


@dataclass
class TranscriptSegment:
    """트랜스크립트 세그먼트"""
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    """트랜스크립션 결과"""
    segments: list[TranscriptSegment] = field(default_factory=list)
    language: str = ""
    full_text: str = ""


class TranscriptionService:
    """OpenAI Whisper API 기반 음성-텍스트 변환 서비스"""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_whisper_model
        self.chunk_size_mb = settings.whisper_chunk_size_mb
        self.retry_count = settings.ai_retry_count
        self.retry_delay = settings.ai_retry_delay

    async def transcribe(
        self,
        audio_path: str,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> TranscriptionResult:
        """
        오디오 파일을 텍스트로 변환

        Args:
            audio_path: WAV 파일 경로
            on_progress: 진행 상황 콜백

        Returns:
            TranscriptionResult

        Raises:
            FileNotFoundError: 오디오 파일 없음
            RuntimeError: Whisper API 호출 실패
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {audio_path}")

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

        if file_size_mb <= self.chunk_size_mb:
            return await self._transcribe_single(audio_path)

        # 큰 파일 → 청크 분할
        chunk_paths = await asyncio.to_thread(
            self._split_audio, audio_path, self.chunk_size_mb
        )

        try:
            return await self._transcribe_chunks(chunk_paths, on_progress)
        finally:
            # 청크 임시 파일 정리
            for path in chunk_paths:
                if os.path.exists(path):
                    os.remove(path)

    async def _transcribe_single(self, audio_path: str) -> TranscriptionResult:
        """단일 파일 Whisper API 호출"""
        for attempt in range(self.retry_count):
            try:
                with open(audio_path, "rb") as audio_file:
                    response = await self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                    )

                segments = []
                for seg in (response.segments or []):
                    segments.append(TranscriptSegment(
                        start=seg.get("start", seg.start) if hasattr(seg, "start") else seg["start"],
                        end=seg.get("end", seg.end) if hasattr(seg, "end") else seg["end"],
                        text=(seg.get("text", seg.text) if hasattr(seg, "text") else seg["text"]).strip(),
                    ))

                return TranscriptionResult(
                    segments=segments,
                    language=getattr(response, "language", ""),
                    full_text=response.text.strip() if response.text else "",
                )

            except Exception as e:
                if attempt == self.retry_count - 1:
                    raise RuntimeError(f"Whisper API 호출 실패: {e}") from e
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

    def _split_audio(self, audio_path: str, chunk_size_mb: int) -> list[str]:
        """큰 오디오 파일을 청크로 분할 (pydub 사용)"""
        from pydub import AudioSegment

        audio = AudioSegment.from_wav(audio_path)

        # 파일 크기 기준으로 청크 시간 계산
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        duration_ms = len(audio)
        ms_per_mb = duration_ms / file_size_mb
        chunk_duration_ms = int(ms_per_mb * chunk_size_mb)

        chunk_paths = []
        base_dir = os.path.dirname(audio_path)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]

        for i, start_ms in enumerate(range(0, duration_ms, chunk_duration_ms)):
            end_ms = min(start_ms + chunk_duration_ms, duration_ms)
            chunk = audio[start_ms:end_ms]

            chunk_path = os.path.join(base_dir, f"{base_name}_chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")
            chunk_paths.append(chunk_path)

        return chunk_paths

    async def _transcribe_chunks(
        self,
        chunk_paths: list[str],
        on_progress: Callable[[str], Awaitable[None]] | None,
    ) -> TranscriptionResult:
        """청크별 Whisper 호출 후 결과 병합"""
        all_segments: list[TranscriptSegment] = []
        all_texts: list[str] = []
        language = ""
        time_offset = 0.0

        for i, chunk_path in enumerate(chunk_paths):
            if on_progress:
                msg = AI_PROCESSING_MESSAGES["stt_chunking"].format(
                    current=i + 1, total=len(chunk_paths)
                )
                await on_progress(msg)

            result = await self._transcribe_single(chunk_path)

            if not language and result.language:
                language = result.language

            # 타임스탬프에 오프셋 추가
            for seg in result.segments:
                all_segments.append(TranscriptSegment(
                    start=seg.start + time_offset,
                    end=seg.end + time_offset,
                    text=seg.text,
                ))

            all_texts.append(result.full_text)

            # 다음 청크의 오프셋 = 현재 청크 마지막 세그먼트 끝 시간
            if result.segments:
                time_offset += result.segments[-1].end

        return TranscriptionResult(
            segments=all_segments,
            language=language,
            full_text=" ".join(all_texts),
        )
