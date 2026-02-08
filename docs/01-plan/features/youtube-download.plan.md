# Plan: youtube-download

> Feature: YouTube 영상 실제 다운로드 및 파일 업로드 저장 구현
> Created: 2026-02-08
> Level: Dynamic

## 1. 배경

현재 `VideoProcessor`는 **전체가 Mock 시뮬레이션**:
- YouTube URL 입력 → `sleep()` 후 하드코딩된 하이라이트 5개 INSERT
- 파일 업로드 → `sleep()` 후 동일한 Mock 하이라이트 INSERT
- **실제 영상 파일이 디스크에 저장되지 않음** → Export/Download 기능 불가

이로 인해 highlight-download 기능이 완성되었음에도 "Source video not found" 에러 발생.

## 2. 목표

YouTube URL 및 파일 업로드 시 **실제 영상 파일을 디스크에 저장**하여, FFmpeg Export → Download까지 **End-to-End 동작하는 파이프라인 완성**

## 3. 요구사항

### 3.1 YouTube 다운로드 (yt-dlp)

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| YT-1 | yt-dlp로 YouTube 영상을 `uploads/{video_id}.mp4`로 다운로드 | P0 |
| YT-2 | 다운로드 진행률을 DB에 업데이트 (실시간 progress) | P1 |
| YT-3 | YouTube 영상 제목을 video.title에 반영 | P1 |
| YT-4 | 영상 duration을 실제 값으로 저장 | P1 |
| YT-5 | yt-dlp 미설치 시 명확한 에러 메시지 | P0 |

### 3.2 파일 업로드 저장

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| UP-1 | 업로드된 파일을 `uploads/{video_id}_{filename}`으로 디스크 저장 | P0 |
| UP-2 | 저장 경로를 video.source_filename에 정확히 기록 | P0 |
| UP-3 | 업로드 진행률 업데이트 | P1 |

### 3.3 AI 분석은 Out of Scope

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| AI-1 | 하이라이트 분석은 현재 Mock 유지 | - |
| AI-2 | 추후 별도 feature (ai-highlight-analysis)로 구현 | - |

## 4. 현재 코드 분석

### Mock 부분 (수정 대상)

| 파일 | 현재 동작 | 변경 필요 |
|------|----------|----------|
| `services/video_processor.py` | `process_youtube()`: sleep 후 mock 분석 | yt-dlp로 실제 다운로드 후 mock 분석 |
| `services/video_processor.py` | `process_file()`: sleep 후 mock 분석 | 파일을 디스크에 저장 후 mock 분석 |
| `api/videos.py` | `upload_video()`: 파일 객체를 백그라운드로 전달만 | 동일 (processor에서 저장) |

### 유지 부분 (변경 없음)

| 파일 | 이유 |
|------|------|
| `api/highlights.py` | Export/Download 엔드포인트 정상 |
| `services/export_processor.py` | FFmpeg 클리핑 정상 (소스 파일만 있으면 동작) |
| `frontend/*` | 변경 불필요 |
| `infrastructure/*` | DB/Repository 변경 없음 |

## 5. 구현 범위

### In Scope
- yt-dlp 설치 및 YouTube 영상 다운로드
- 업로드 파일 디스크 저장
- 다운로드/저장 진행률 DB 반영
- YouTube 메타정보 (제목, 길이) 반영
- yt-dlp 미설치 에러 처리

### Out of Scope
- AI 하이라이트 분석 (Whisper STT, 감정 분석 등) → 별도 feature
- YouTube 자막/썸네일 다운로드
- 영상 화질 선택 UI
- 다운로드 캐시/중복 방지

## 6. 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| YouTube 다운로드 | `yt-dlp` | pip install yt-dlp |
| 파일 저장 | `aiofiles` 또는 동기 파일 I/O | FastAPI UploadFile → 디스크 |
| 진행률 콜백 | yt-dlp `progress_hooks` | 다운로드 % → DB update |
| 메타정보 | yt-dlp `extract_info` | 제목, duration 추출 |

## 7. 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/requirements.txt` | `yt-dlp` 추가 |
| `backend/src/services/video_processor.py` | YouTube 다운로드 + 파일 저장 로직 |
| `backend/src/core/config.py` | upload_dir 관련 설정 확인 (변경 최소) |

## 8. 리스크

| 리스크 | 완화 방안 |
|--------|----------|
| yt-dlp 미설치 환경 | `_check_ytdlp()` 체크 후 에러 메시지 |
| YouTube 영상 다운로드 속도 | progress_hooks로 사용자에게 진행률 표시 |
| 대용량 영상 디스크 공간 | upload_dir 용량 체크는 추후 대응 |
| yt-dlp 버전/API 변경 | requirements.txt에 버전 고정 |
| YouTube 저작권/차단 | 사용자 책임, 에러 시 메시지 안내 |
| asyncio + yt-dlp 호환 | yt-dlp는 동기 → `asyncio.to_thread()`로 래핑 |
