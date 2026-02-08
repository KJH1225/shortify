# Design: real-ai-integration

> Feature: Mock AI 분석을 실제 AI 하이라이트 추출 파이프라인으로 교체
> Plan: `docs/01-plan/features/real-ai-integration.plan.md`
> Created: 2026-02-08

## 1. 구현 순서

```
1. [BE] core/config.py        - OpenAI 모델 설정 추가 + API 키 유효성 검증
2. [BE] core/constants.py     - AI 프롬프트 상수 추가
3. [BE] services/audio_extractor.py    - (신규) FFmpeg 오디오 추출 서비스
4. [BE] services/transcription_service.py - (신규) Whisper API STT 서비스
5. [BE] services/highlight_analyzer.py - (신규) GPT-4o-mini 하이라이트 분석 서비스
6. [BE] services/video_processor.py    - _simulate_analysis() → _analyze_video() 교체
7. [BE] requirements.txt      - pydub 의존성 추가
```

## 2. 아키텍처 개요

```
VideoProcessor
    │
    ├── process_file() ──────────┐
    │                            │
    └── process_youtube() ───────┤
                                 ▼
                     _analyze_video(video_id)
                          │
          ┌───────────────┼───────────────────┐
          ▼               ▼                   ▼
   AudioExtractor  TranscriptionService  HighlightAnalyzer
   (FFmpeg)        (Whisper API)         (GPT-4o-mini)
```

**설계 원칙**:
- 각 서비스는 **단일 책임** (추출, STT, 분석)
- `VideoProcessor`가 오케스트레이터 역할
- 서비스 간 의존성 없음 (데이터만 전달)
- API 키 미설정 시 기존 Mock 폴백 유지

## 3. Backend 설계

### 3.1 Settings 확장

**파일**: `backend/src/core/config.py`

```python
class Settings(BaseSettings):
    # ... 기존 설정

    # OpenAI
    openai_api_key: str = ""
    openai_whisper_model: str = "whisper-1"
    openai_chat_model: str = "gpt-4o-mini"

    # AI 분석 설정
    audio_sample_rate: int = 16000          # Whisper 권장 16kHz
    whisper_chunk_size_mb: int = 24         # 25MB 제한 → 24MB로 안전 마진
    max_highlights: int = 10               # 최대 하이라이트 수
    ai_retry_count: int = 3               # API 재시도 횟수
    ai_retry_delay: float = 2.0           # 재시도 기본 대기 (초)

    def has_openai_key(self) -> bool:
        """OpenAI API 키가 설정되었는지 확인"""
        return bool(self.openai_api_key and self.openai_api_key.strip())
```

### 3.2 AI 프롬프트 상수

**파일**: `backend/src/core/constants.py` (추가)

```python
# AI Highlight Analysis Prompt
HIGHLIGHT_SYSTEM_PROMPT = """You are a professional video highlight extraction expert.
Analyze the transcript and extract the most engaging, valuable segments.

Selection criteria:
- Key concepts or important information delivery
- Emotionally impactful moments
- Surprising insights or turning points
- Practical tips and advice
- Segments that attract viewer attention

Rules:
- Each highlight must be 15-60 seconds long
- Highlights must not overlap
- Score reflects importance (0.0-1.0, higher = more important)
- Title should be concise (under 20 characters)
- Description should explain why this segment is valuable (under 50 characters)
- Respond in the same language as the transcript"""

HIGHLIGHT_USER_PROMPT = """Video duration: {duration} seconds
Target highlight count: {target_count}

Transcript:
{transcript}

Extract highlights as JSON array:
[
  {{
    "start_time": <start seconds>,
    "end_time": <end seconds>,
    "title": "<highlight title>",
    "description": "<why this segment matters>",
    "score": <0.0-1.0>
  }}
]"""

# AI 처리 진행 메시지 (실제 파이프라인용)
AI_PROCESSING_MESSAGES = {
    "audio_extract_start": "오디오 트랙 추출 중...",
    "audio_extract_done": "오디오 추출 완료",
    "stt_start": "음성을 텍스트로 변환 중...",
    "stt_chunking": "긴 오디오 분할 처리 중... ({current}/{total} 청크)",
    "stt_done": "음성 인식 완료 ({segment_count}개 세그먼트)",
    "analysis_start": "AI가 하이라이트 구간 분석 중...",
    "analysis_done": "하이라이트 {count}개 추출 완료",
    "saving": "결과 저장 중...",
    "completed": "AI 분석이 완료되었습니다!",
    "fallback_mock": "AI 분석을 사용할 수 없어 기본 하이라이트를 생성합니다.",
}
```

### 3.3 AudioExtractor 서비스

**파일**: `backend/src/services/audio_extractor.py` (신규)

**책임**: 영상 파일 → WAV 오디오 추출

```python
class AudioExtractor:
    """FFmpeg를 사용한 오디오 추출 서비스"""

    async def extract(self, video_path: str, output_path: str) -> str:
        """
        영상에서 오디오를 WAV로 추출

        Args:
            video_path: 입력 영상 파일 경로
            output_path: 출력 오디오 파일 경로

        Returns:
            출력 파일 경로

        Raises:
            FileNotFoundError: 영상 파일 없음
            RuntimeError: FFmpeg 미설치 또는 실행 실패
        """

    def _check_ffmpeg(self) -> bool:
        """FFmpeg 설치 여부 확인"""
```

**FFmpeg 명령어**:
```bash
ffmpeg -y -i {video_path} -vn -acodec pcm_s16le -ar 16000 -ac 1 {output_path}
```

| 옵션 | 설명 |
|------|------|
| `-y` | 출력 파일 덮어쓰기 |
| `-vn` | 비디오 스트림 제거 |
| `-acodec pcm_s16le` | 16-bit PCM WAV |
| `-ar 16000` | 16kHz 샘플레이트 (Whisper 권장) |
| `-ac 1` | 모노 채널 |

**실행 방식**: `asyncio.create_subprocess_exec()` (export_processor와 동일 패턴)

**에러 처리**:
| 상황 | 예외 | 메시지 |
|------|------|--------|
| FFmpeg 미설치 | `RuntimeError` | "FFmpeg가 설치되지 않았습니다" |
| 영상 파일 없음 | `FileNotFoundError` | "영상 파일을 찾을 수 없습니다: {path}" |
| FFmpeg 실행 실패 | `RuntimeError` | "오디오 추출 실패: {stderr}" |

### 3.4 TranscriptionService 서비스

**파일**: `backend/src/services/transcription_service.py` (신규)

**책임**: WAV 오디오 → 타임스탬프 포함 트랜스크립트

```python
@dataclass
class TranscriptSegment:
    """트랜스크립트 세그먼트"""
    start: float       # 시작 시간 (초)
    end: float         # 종료 시간 (초)
    text: str          # 텍스트 내용

@dataclass
class TranscriptionResult:
    """트랜스크립션 결과"""
    segments: list[TranscriptSegment]
    language: str       # 감지된 언어 (ko, en, ...)
    full_text: str      # 전체 텍스트 (세그먼트 결합)


class TranscriptionService:
    """OpenAI Whisper API 기반 음성-텍스트 변환 서비스"""

    def __init__(self):
        self.client: AsyncOpenAI  # openai.AsyncOpenAI

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
            TranscriptionResult (세그먼트 목록 + 언어 + 전체 텍스트)
        """

    async def _transcribe_single(self, audio_path: str) -> dict:
        """단일 파일 Whisper API 호출 (25MB 이하)"""

    def _split_audio(self, audio_path: str, chunk_size_mb: int) -> list[str]:
        """큰 오디오 파일을 청크로 분할 (pydub 사용)"""

    async def _transcribe_chunks(
        self,
        chunk_paths: list[str],
        on_progress: Callable | None,
    ) -> TranscriptionResult:
        """청크별 Whisper 호출 후 결과 병합"""
```

**Whisper API 호출 상세**:

```python
response = await self.client.audio.transcriptions.create(
    model="whisper-1",
    file=open(audio_path, "rb"),
    response_format="verbose_json",
    timestamp_granularities=["segment"],
)
```

| 파라미터 | 값 | 이유 |
|---------|-----|------|
| `model` | `"whisper-1"` | 현재 유일한 Whisper 모델 |
| `response_format` | `"verbose_json"` | 세그먼트별 타임스탬프 포함 |
| `timestamp_granularities` | `["segment"]` | 문장 단위 타임스탬프 |

**청크 분할 전략**:

```
파일 크기 확인 (os.path.getsize)
    │
    ├── <= 24MB → _transcribe_single() 직접 호출
    │
    └── > 24MB → _split_audio()
                    │
                    ├── pydub로 10분 단위 청크 분할
                    ├── 각 청크를 임시 WAV로 저장
                    └── _transcribe_chunks()로 순차 처리
                          │
                          └── 각 청크 결과의 타임스탬프에
                              누적 오프셋 추가하여 병합
```

**타임스탬프 오프셋 병합**:
```
청크 1 (0:00~10:00): segments with timestamps 0~600
청크 2 (10:00~20:00): segments with timestamps 0~600 → offset +600 → 600~1200
청크 3 (20:00~25:00): segments with timestamps 0~300 → offset +1200 → 1200~1500
```

**재시도 로직**:
```python
for attempt in range(settings.ai_retry_count):
    try:
        return await self._transcribe_single(path)
    except openai.APIError as e:
        if attempt == settings.ai_retry_count - 1:
            raise
        await asyncio.sleep(settings.ai_retry_delay * (2 ** attempt))  # exponential backoff
```

### 3.5 HighlightAnalyzer 서비스

**파일**: `backend/src/services/highlight_analyzer.py` (신규)

**책임**: 트랜스크립트 → 하이라이트 JSON 추출

```python
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
        self.client: AsyncOpenAI

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
            하이라이트 목록 (score 내림차순 정렬)
        """

    def _build_transcript_text(self, transcript: TranscriptionResult) -> str:
        """세그먼트를 타임스탬프 포함 텍스트로 포맷"""

    def _calculate_target_count(self, duration: float) -> int:
        """영상 길이에 비례한 목표 하이라이트 수 계산"""

    def _parse_response(self, content: str) -> list[HighlightResult]:
        """GPT 응답 JSON 파싱 + 유효성 검증"""

    def _validate_highlights(
        self,
        highlights: list[HighlightResult],
        duration: float,
    ) -> list[HighlightResult]:
        """하이라이트 유효성 검증 (시간 범위, 중복 제거)"""
```

**GPT-4o-mini API 호출**:

```python
response = await self.client.chat.completions.create(
    model=settings.openai_chat_model,  # "gpt-4o-mini"
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
```

| 파라미터 | 값 | 이유 |
|---------|-----|------|
| `model` | `gpt-4o-mini` | 비용 효율 ($0.15/1M input) |
| `response_format` | `json_object` | JSON 파싱 보장 |
| `temperature` | `0.3` | 일관된 분석 결과 |
| `max_tokens` | `2000` | 최대 10개 하이라이트 충분 |

**트랜스크립트 포맷팅**:
```
[00:00:45] 안녕하세요 오늘은 파이썬에 대해 알아보겠습니다.
[00:01:12] 첫 번째로 변수에 대해 설명하겠습니다.
[00:02:30] 이것이 바로 중요한 포인트입니다!
...
```

**하이라이트 수 계산**:
```python
def _calculate_target_count(self, duration: float) -> int:
    minutes = duration / 60
    count = max(1, min(int(minutes), settings.max_highlights))
    return count
    # 1분 → 1개, 5분 → 5개, 10분 → 10개, 15분+ → 10개(최대)
```

**유효성 검증**:

| 검증 항목 | 조건 | 처리 |
|----------|------|------|
| start_time >= 0 | 음수 불허 | 0으로 클램핑 |
| end_time <= duration | 영상 길이 초과 | duration으로 클램핑 |
| end_time > start_time | 역전 불허 | 해당 하이라이트 제거 |
| 길이 15~60초 | 범위 밖 | 15s 미만 → 15s로, 60s 초과 → 60s로 조정 |
| score 0.0~1.0 | 범위 밖 | 클램핑 |
| 구간 겹침 | 중복 | 낮은 score 하이라이트 제거 |

**재시도 로직**: TranscriptionService와 동일 패턴 (exponential backoff, 최대 3회)

### 3.6 VideoProcessor 수정

**파일**: `backend/src/services/video_processor.py`

**변경 사항**: `_simulate_analysis()` → `_analyze_video()` 교체

```python
class VideoProcessor:
    def __init__(self):
        self._download_progress: dict[int, int] = {}
        self._audio_extractor = AudioExtractor()
        self._transcription_service = TranscriptionService()
        self._highlight_analyzer = HighlightAnalyzer()

    async def _analyze_video(self, video_id: int):
        """실제 AI 분석 파이프라인 (Mock 폴백 포함)"""

        # API 키 확인 → 없으면 Mock 폴백
        if not get_settings().has_openai_key():
            await self._simulate_analysis(video_id)
            return

        try:
            # === Step 1: 오디오 추출 (10-20%) ===
            await self._update_progress(video_id, 10, AI_PROCESSING_MESSAGES["audio_extract_start"])

            video_path = self._get_video_path(video_id)
            audio_path = self._get_audio_path(video_id)
            await self._audio_extractor.extract(video_path, audio_path)

            await self._update_progress(video_id, 20, AI_PROCESSING_MESSAGES["audio_extract_done"])

            # === Step 2: STT (20-50%) ===
            await self._update_progress(video_id, 25, AI_PROCESSING_MESSAGES["stt_start"])

            transcript = await self._transcription_service.transcribe(
                audio_path,
                on_progress=lambda msg: self._update_progress(video_id, -1, msg),
            )

            await self._update_progress(
                video_id, 50,
                AI_PROCESSING_MESSAGES["stt_done"].format(segment_count=len(transcript.segments)),
            )

            # === Step 3: 하이라이트 분석 (50-90%) ===
            await self._update_progress(video_id, 55, AI_PROCESSING_MESSAGES["analysis_start"])

            duration = await self._get_video_duration(video_id)
            highlights = await self._highlight_analyzer.analyze(transcript, duration)

            await self._update_progress(
                video_id, 90,
                AI_PROCESSING_MESSAGES["analysis_done"].format(count=len(highlights)),
            )

            # === Step 4: DB 저장 (90-100%) ===
            await self._update_progress(video_id, 92, AI_PROCESSING_MESSAGES["saving"])
            await self._save_highlights(video_id, highlights)

            # === Step 5: 임시 파일 정리 ===
            self._cleanup_audio(audio_path)

            # === 완료 ===
            await self._complete(video_id)

        except Exception as e:
            # AI 분석 실패 → Mock 폴백
            await self._update_progress(
                video_id, -1,
                AI_PROCESSING_MESSAGES["fallback_mock"],
            )
            await self._simulate_analysis(video_id)

    # === 헬퍼 메서드 ===

    def _get_video_path(self, video_id: int) -> str:
        """영상 파일 경로 결정"""

    def _get_audio_path(self, video_id: int) -> str:
        """오디오 출력 경로 (uploads/audio/{video_id}.wav)"""

    async def _get_video_duration(self, video_id: int) -> float:
        """DB에서 영상 길이 조회"""

    async def _update_progress(self, video_id: int, progress: int, message: str):
        """DB 진행률 업데이트 (progress=-1이면 메시지만 변경)"""

    async def _save_highlights(self, video_id: int, highlights: list[HighlightResult]):
        """하이라이트를 DB에 저장"""

    def _cleanup_audio(self, audio_path: str):
        """임시 오디오 파일 삭제"""

    async def _complete(self, video_id: int):
        """video.status = COMPLETED 설정"""

    async def _simulate_analysis(self, video_id: int):
        """기존 Mock 분석 (폴백용, 유지)"""
```

**호출 변경점**:

| 위치 | 변경 전 | 변경 후 |
|------|---------|---------|
| `process_file()` 마지막 줄 | `await self._simulate_analysis(video_id)` | `await self._analyze_video(video_id)` |
| `process_youtube()` 마지막 줄 | `await self._simulate_analysis(video_id)` | `await self._analyze_video(video_id)` |

**영상 파일 경로 결정 로직**:
```python
def _get_video_path(self, video_id: int) -> str:
    upload_dir = Path(get_settings().upload_dir)
    # YouTube: {video_id}.mp4
    mp4_path = upload_dir / f"{video_id}.mp4"
    if mp4_path.exists():
        return str(mp4_path)
    # File upload: {video_id}_{filename} 패턴 검색
    for f in upload_dir.iterdir():
        if f.name.startswith(f"{video_id}_"):
            return str(f)
    raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: video_id={video_id}")
```

## 4. 데이터 흐름 상세

```
                        _analyze_video(video_id)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            has_openai_key()?     [No] _simulate_analysis()
                    │ [Yes]              (기존 Mock 유지)
                    ▼
         ┌──── AudioExtractor.extract() ────┐
         │  video.mp4 → audio.wav (16kHz)   │
         │  Progress: 10% → 20%             │
         └──────────────┬───────────────────┘
                        ▼
         ┌──── TranscriptionService.transcribe() ──┐
         │  audio.wav → TranscriptionResult        │
         │  (segments[], language, full_text)       │
         │  Progress: 20% → 50%                    │
         │                                         │
         │  [파일 > 24MB?]                          │
         │    Yes → _split_audio() → 청크별 처리     │
         │    No  → _transcribe_single() 직접 호출   │
         └──────────────┬──────────────────────────┘
                        ▼
         ┌──── HighlightAnalyzer.analyze() ────────┐
         │  transcript + duration → highlights[]   │
         │  GPT-4o-mini (JSON mode)                │
         │  Progress: 50% → 90%                    │
         │                                         │
         │  결과 검증:                               │
         │  - 시간 범위 클램핑                        │
         │  - 중복 구간 제거                          │
         │  - score 정렬                             │
         └──────────────┬──────────────────────────┘
                        ▼
         ┌──── _save_highlights() ─────────────────┐
         │  HighlightRepository.create_batch()     │
         │  Progress: 90% → 100%                   │
         └──────────────┬──────────────────────────┘
                        ▼
         ┌──── _cleanup_audio() ───────────────────┐
         │  임시 WAV/청크 파일 삭제                   │
         └──────────────┬──────────────────────────┘
                        ▼
                video.status = COMPLETED
```

## 5. 에러 처리 전략

### 5.1 에러 계층

```
_analyze_video()
    │
    ├── [FFmpeg 에러]
    │     RuntimeError("FFmpeg 미설치") → Mock 폴백
    │     RuntimeError("오디오 추출 실패") → Mock 폴백
    │
    ├── [Whisper API 에러]
    │     openai.APIError → 재시도 3회 → Mock 폴백
    │     openai.AuthenticationError → Mock 폴백 (키 무효)
    │     openai.RateLimitError → 재시도 (exponential backoff)
    │
    ├── [GPT-4 에러]
    │     openai.APIError → 재시도 3회 → Mock 폴백
    │     JSON 파싱 실패 → 재시도 → Mock 폴백
    │     빈 결과 → "하이라이트를 찾지 못했습니다" 메시지
    │
    └── [예상치 못한 에러]
          Exception → Mock 폴백 + 에러 로그
```

### 5.2 폴백 원칙

| 단계 | 실패 시 | 사용자 메시지 |
|------|---------|-------------|
| 오디오 추출 | Mock 폴백 | "AI 분석을 사용할 수 없어 기본 하이라이트를 생성합니다" |
| Whisper STT | Mock 폴백 | 동일 |
| GPT 분석 | Mock 폴백 | 동일 |
| 빈 트랜스크립트 | Mock 폴백 | "음성이 감지되지 않아 기본 하이라이트를 생성합니다" |
| DB 저장 실패 | video.status = ERROR | "결과 저장 중 오류가 발생했습니다" |

**핵심**: AI 파이프라인의 어떤 단계에서 실패하든, 사용자는 항상 하이라이트를 받을 수 있어야 함 (Mock이라도)

## 6. 진행률 매핑

| 진행률 (%) | 단계 | 메시지 |
|-----------|------|--------|
| 10 | 오디오 추출 시작 | "오디오 트랙 추출 중..." |
| 20 | 오디오 추출 완료 | "오디오 추출 완료" |
| 25 | STT 시작 | "음성을 텍스트로 변환 중..." |
| 25~50 | STT 진행 (청크별) | "긴 오디오 분할 처리 중... (2/5 청크)" |
| 50 | STT 완료 | "음성 인식 완료 (45개 세그먼트)" |
| 55 | 분석 시작 | "AI가 하이라이트 구간 분석 중..." |
| 90 | 분석 완료 | "하이라이트 5개 추출 완료" |
| 92 | DB 저장 | "결과 저장 중..." |
| 100 | 전체 완료 | "AI 분석이 완료되었습니다!" |

## 7. 파일 시스템 구조

```
uploads/
├── {video_id}.mp4              # YouTube 다운로드 영상
├── {video_id}_{filename}       # 업로드 영상
├── audio/                      # 임시 오디오 (분석 후 삭제)
│   ├── {video_id}.wav          # 추출된 오디오
│   ├── {video_id}_chunk_0.wav  # 청크 (필요 시)
│   ├── {video_id}_chunk_1.wav
│   └── ...
└── exports/                    # Export 결과 (기존)
    └── {highlight_id}_{start}_{end}.mp4
```

## 8. 의존성 변경

**파일**: `backend/requirements.txt`

```diff
+ pydub>=0.25.1
```

**pydub 선택 이유**:
- FFmpeg 래퍼로 오디오 청크 분할에 최적
- 설치 간단 (`pip install pydub`)
- FFmpeg가 이미 있으므로 별도 바이너리 불필요

**기존 의존성 활용**:
| 패키지 | 이미 설치 | 용도 |
|--------|:---------:|------|
| `openai>=1.57.0` | O | Whisper API + GPT-4o-mini |
| `httpx>=0.28.0` | O | openai 내부 HTTP 클라이언트 |

## 9. 변경 없는 파일 (확인)

| 파일 | 이유 |
|------|------|
| `api/videos.py` | 엔드포인트 시그니처 변경 없음 |
| `api/highlights.py` | Export/Download 무관 |
| `services/export_processor.py` | FFmpeg 클리핑 무관 |
| `infrastructure/models.py` | Highlight 모델 스키마 동일 |
| `infrastructure/repository.py` | `create_batch()` 인터페이스 동일 |
| `infrastructure/database.py` | DB 연결 변경 없음 |
| `models/schemas.py` | Pydantic 모델 변경 없음 |
| `frontend/*` | 프론트엔드 변경 없음 |

## 10. 검증 항목

| ID | 검증 항목 | 방법 |
|----|----------|------|
| V-1 | FFmpeg 오디오 추출이 WAV 16kHz mono로 출력되는지 | 영상 업로드 후 audio/ 디렉토리 확인 |
| V-2 | Whisper API가 segment-level 타임스탬프를 반환하는지 | 로그에서 TranscriptionResult 확인 |
| V-3 | 25MB 초과 오디오가 청크 분할되는지 | 긴 영상 (30분+) 테스트 |
| V-4 | 청크별 타임스탬프 오프셋이 정확한지 | 두 번째 청크의 start_time 확인 |
| V-5 | GPT-4o-mini가 유효한 JSON을 반환하는지 | 응답 파싱 로그 확인 |
| V-6 | 하이라이트 시간이 영상 범위 내인지 | DB에 저장된 start/end_time 확인 |
| V-7 | 하이라이트 구간이 겹치지 않는지 | DB 데이터 검증 |
| V-8 | API 키 미설정 시 Mock 폴백이 동작하는지 | API 키 없이 업로드 테스트 |
| V-9 | Whisper 실패 시 Mock 폴백이 동작하는지 | 잘못된 API 키로 테스트 |
| V-10 | 진행률이 10→20→50→90→100 순서로 증가하는지 | 프론트엔드에서 progress 폴링 확인 |
| V-11 | 임시 오디오 파일이 분석 후 삭제되는지 | audio/ 디렉토리 사후 확인 |
| V-12 | 기존 Export/Download 기능이 정상 동작하는지 | AI 분석 후 highlight export 테스트 |
