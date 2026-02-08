# Plan: real-ai-integration

> Feature: Mock AI 분석을 실제 AI 하이라이트 추출 파이프라인으로 교체
> Created: 2026-02-08
> Level: Dynamic

## 1. 배경

현재 `VideoProcessor._simulate_analysis()`는 **완전한 Mock**:
- `MOCK_HIGHLIGHTS_DATA` 상수에서 하드코딩된 5개 하이라이트를 INSERT
- `PROCESSING_MESSAGES`를 0.8초 간격으로 순회하며 가짜 진행률 표시
- 실제 영상 내용과 **무관한** 고정된 타임스탬프 (45s, 120s, 210s, 300s, 420s)

영상 파일은 이미 디스크에 저장되고 (`uploads/{video_id}.mp4`), FFmpeg Export도 동작하지만, **AI 분석 자체가 가짜**이므로 하이라이트 품질이 의미 없음.

## 2. 목표

업로드/다운로드된 영상을 **실제 AI로 분석**하여, 영상 내용 기반의 하이라이트 구간을 자동 추출하는 파이프라인 구현

### 핵심 가치
- 영상의 **실제 대화/나레이션**을 STT로 텍스트화
- GPT-4로 텍스트를 분석하여 **흥미로운 구간** 자동 판별
- 각 하이라이트에 대해 **제목, 설명, 점수**를 AI가 생성

## 3. 요구사항

### 3.1 오디오 추출 (FFmpeg)

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| AE-1 | 영상 파일에서 오디오를 WAV/MP3로 추출 (FFmpeg) | P0 |
| AE-2 | 추출된 오디오를 `uploads/audio/{video_id}.wav`에 저장 | P0 |
| AE-3 | 오디오 추출 진행률 DB 업데이트 (10~20%) | P1 |
| AE-4 | FFmpeg 미설치 시 명확한 에러 메시지 | P0 |

### 3.2 음성-텍스트 변환 (Whisper API)

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| STT-1 | OpenAI Whisper API로 오디오를 텍스트로 변환 | P0 |
| STT-2 | 타임스탬프 포함 트랜스크립트 반환 (segment-level timestamps) | P0 |
| STT-3 | 긴 오디오 (>25MB) 청크 분할 후 순차 처리 | P0 |
| STT-4 | 한국어/영어 자동 언어 감지 | P1 |
| STT-5 | STT 진행률 DB 업데이트 (20~50%) | P1 |
| STT-6 | Whisper API 실패 시 재시도 (최대 3회) | P1 |

### 3.3 하이라이트 분석 (GPT-4)

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| HL-1 | 트랜스크립트를 GPT-4에 전달하여 하이라이트 구간 추출 | P0 |
| HL-2 | 각 하이라이트: start_time, end_time, title, description, score 반환 | P0 |
| HL-3 | 영상 길이에 비례한 하이라이트 수 (1분당 ~1개, 최소 1개 최대 10개) | P1 |
| HL-4 | JSON 형식으로 구조화된 응답 (Structured Output) | P0 |
| HL-5 | 분석 진행률 DB 업데이트 (50~90%) | P1 |
| HL-6 | GPT-4 응답 파싱 실패 시 재시도 | P1 |

### 3.4 파이프라인 통합

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| PL-1 | `_simulate_analysis()` → `_analyze_video()` 교체 | P0 |
| PL-2 | 파이프라인 단계별 진행률: 추출(10-20%) → STT(20-50%) → 분석(50-90%) → 저장(90-100%) | P0 |
| PL-3 | 어느 단계에서든 실패 시 video.status = ERROR + 에러 메시지 저장 | P0 |
| PL-4 | OpenAI API 키 미설정 시 Mock 모드로 폴백 (기존 동작 유지) | P1 |
| PL-5 | 임시 오디오 파일 분석 완료 후 삭제 | P2 |

## 4. 현재 코드 분석

### 수정 대상

| 파일 | 현재 동작 | 변경 필요 |
|------|----------|----------|
| `services/video_processor.py` | `_simulate_analysis()`: Mock 데이터 INSERT | 실제 AI 파이프라인으로 교체 |
| `core/config.py` | `openai_api_key: str = ""` | 키 유효성 검증 메서드 추가 |
| `core/constants.py` | `MOCK_HIGHLIGHTS_DATA`, `PROCESSING_MESSAGES` | AI 프롬프트 상수 추가, Mock 데이터는 폴백용 유지 |

### 신규 파일

| 파일 | 역할 |
|------|------|
| `services/audio_extractor.py` | FFmpeg 오디오 추출 서비스 |
| `services/transcription_service.py` | Whisper API 호출 + 청크 분할 |
| `services/highlight_analyzer.py` | GPT-4 하이라이트 분석 + JSON 파싱 |

### 유지 부분 (변경 없음)

| 파일 | 이유 |
|------|------|
| `api/videos.py` | 엔드포인트 변경 없음 (processor 내부만 변경) |
| `api/highlights.py` | Export/Download 변경 없음 |
| `services/export_processor.py` | FFmpeg 클리핑 변경 없음 |
| `infrastructure/*` | DB 모델/Repository 변경 없음 |
| `frontend/*` | 프론트엔드 변경 없음 (진행 메시지만 달라짐) |

## 5. AI 파이프라인 흐름

```
영상 파일 (uploads/{video_id}.mp4)
    │
    ▼ [Step 1: 오디오 추출] (10-20%)
FFmpeg: video → audio.wav (16kHz, mono)
    │
    ▼ [Step 2: 청크 분할] (필요 시)
긴 오디오 → 25MB 이하 청크들로 분할
    │
    ▼ [Step 3: STT] (20-50%)
Whisper API → 타임스탬프 포함 트랜스크립트
    │
    ▼ [Step 4: 하이라이트 분석] (50-90%)
GPT-4: 트랜스크립트 → 하이라이트 JSON
    │
    ▼ [Step 5: DB 저장] (90-100%)
highlights 테이블에 INSERT → video.status = COMPLETED
```

## 6. GPT-4 프롬프트 설계 (초안)

```
당신은 영상 하이라이트 추출 전문가입니다.
아래 영상 트랜스크립트를 분석하여 가장 흥미롭고 가치있는 구간들을 추출하세요.

선정 기준:
- 핵심 개념이나 중요 정보가 전달되는 구간
- 감정적으로 임팩트 있는 순간
- 놀라운 반전이나 인사이트
- 실용적인 팁/조언
- 시청자의 관심을 끌 수 있는 구간

영상 전체 길이: {duration}초
트랜스크립트: {transcript}

JSON 형식으로 응답:
[
  {
    "start_time": 시작 시간(초),
    "end_time": 종료 시간(초),
    "title": "하이라이트 제목 (한국어, 20자 이내)",
    "description": "해당 구간 설명 (한국어, 50자 이내)",
    "score": 중요도 점수 (0.0~1.0)
  }
]
```

## 7. 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| 오디오 추출 | FFmpeg (subprocess) | 이미 export_processor에서 사용 중 |
| 음성 인식 | OpenAI Whisper API | `openai>=1.57.0` (이미 설치됨) |
| 텍스트 분석 | OpenAI GPT-4o-mini | 비용 효율적, JSON mode 지원 |
| 청크 분할 | pydub 또는 FFmpeg | Whisper 25MB 제한 대응 |
| 비동기 API | httpx 또는 openai async | `httpx>=0.28.0` (이미 설치됨) |

## 8. 구현 범위

### In Scope
- FFmpeg 오디오 추출 (video → wav)
- Whisper API STT (타임스탬프 포함)
- 긴 오디오 청크 분할 (25MB 제한 대응)
- GPT-4o-mini 하이라이트 분석
- Structured Output (JSON) 파싱
- 단계별 진행률 업데이트
- 에러 처리 및 재시도 로직
- API 키 미설정 시 Mock 폴백

### Out of Scope
- 영상 프레임 분석 (Scene Detection) → 별도 feature
- 썸네일 자동 생성 → thumbnail-generation feature
- 자막 파일 생성 (SRT/VTT) → 별도 feature
- Whisper 로컬 모델 (서버 리소스 필요) → 별도 feature
- 사용자별 프롬프트 커스터마이징 → 별도 feature
- 영상 장르별 분석 전략 분기 → v2

## 9. 수정 대상 파일 요약

| 파일 | 변경 유형 | 변경 내용 |
|------|----------|----------|
| `backend/requirements.txt` | 수정 | `pydub` 추가 (오디오 청크 분할용) |
| `backend/src/services/video_processor.py` | 수정 | `_simulate_analysis()` → 실제 AI 파이프라인 호출 |
| `backend/src/services/audio_extractor.py` | **신규** | FFmpeg 오디오 추출 서비스 |
| `backend/src/services/transcription_service.py` | **신규** | Whisper API STT 서비스 |
| `backend/src/services/highlight_analyzer.py` | **신규** | GPT-4 하이라이트 분석 서비스 |
| `backend/src/core/config.py` | 수정 | `openai_model` 설정 추가 |
| `backend/src/core/constants.py` | 수정 | AI 프롬프트 상수 추가 |

## 10. 비용 추정

| API | 단가 | 10분 영상 예상 비용 |
|-----|------|-------------------|
| Whisper API | $0.006/분 | ~$0.06 |
| GPT-4o-mini (input) | $0.15/1M tokens | ~$0.01 (트랜스크립트 ~2K tokens) |
| GPT-4o-mini (output) | $0.60/1M tokens | ~$0.001 (JSON ~500 tokens) |
| **합계** | | **~$0.07/영상** |

## 11. 리스크

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| OpenAI API 키 미설정 | 분석 불가 | Mock 폴백 모드 유지 (PL-4) |
| Whisper 25MB 제한 | 긴 영상 처리 불가 | 오디오 청크 분할 (STT-3) |
| GPT-4 JSON 파싱 실패 | 하이라이트 미생성 | Structured Output + 재시도 (HL-6) |
| API 호출 지연 (10~30초) | 사용자 대기 | 단계별 진행률로 UX 보완 (PL-2) |
| API 비용 누적 | 운영비 증가 | GPT-4o-mini 사용, 토큰 최적화 |
| FFmpeg 미설치 | 오디오 추출 불가 | 명확한 에러 메시지 (AE-4) |
| 음성 없는 영상 | 빈 트랜스크립트 | 빈 결과 시 Mock 폴백 또는 "하이라이트 없음" 처리 |
| 네트워크 장애 | API 호출 실패 | 재시도 + exponential backoff |

## 12. 성공 기준

| 기준 | 목표 |
|------|------|
| 하이라이트 추출 정확도 | 영상 내용과 관련된 구간 추출 |
| 처리 시간 | 10분 영상 기준 60초 이내 |
| 에러 복구율 | API 일시 오류 시 자동 재시도 성공 |
| Mock 폴백 | API 키 없이도 기존처럼 동작 |
| 비용 효율 | 영상당 $0.10 이하 |
