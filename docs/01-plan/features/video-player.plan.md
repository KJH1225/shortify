# Plan: video-player

> Feature: 인터랙티브 영상 플레이어 + 하이라이트 타임라인 프리뷰
> Created: 2026-02-08
> Level: Dynamic

## 1. 배경

현재 Shortify는 AI 하이라이트 추출 파이프라인이 완성되었지만, **영상 재생 기능이 없음**:
- `page.tsx:122` — `handlePlay()`에 `// TODO: 영상 플레이어 연동` 주석만 존재
- HighlightCard의 Play 버튼 클릭 시 `console.log`만 출력
- 사용자가 하이라이트 구간을 **미리보기할 수 없어** 품질 확인 불가
- Export 전 내용 확인 없이 다운로드해야 하는 UX 문제

## 2. 목표

하이라이트를 클릭하면 해당 구간의 영상을 **즉시 미리볼 수 있는** 인터랙티브 플레이어 구현

### 핵심 가치
- 하이라이트 클릭 → 해당 구간 **자동 시작/자동 종료** 재생
- 타임라인 바에 **하이라이트 구간 시각적 표시**
- 전체 영상 탐색 + 특정 하이라이트 구간 점프 지원

## 3. 요구사항

### 3.1 백엔드: 영상 스트리밍 엔드포인트

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| BE-1 | `GET /api/videos/{video_id}/stream` — 영상 파일 스트리밍 엔드포인트 | P0 |
| BE-2 | HTTP Range Request 지원 (부분 로딩, 시크 지원) | P0 |
| BE-3 | Content-Type 헤더 적절히 설정 (`video/mp4`) | P0 |
| BE-4 | 존재하지 않는 video_id 또는 파일 없음 시 404 응답 | P1 |

### 3.2 프론트엔드: 영상 플레이어 컴포넌트

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FE-1 | `VideoPlayer` 컴포넌트 — HTML5 `<video>` 기반 영상 재생 | P0 |
| FE-2 | Play/Pause, 볼륨, 프로그레스바 기본 컨트롤 | P0 |
| FE-3 | 하이라이트 클릭 시 해당 구간으로 자동 시크 + 재생 시작 | P0 |
| FE-4 | 하이라이트 종료 시간 도달 시 자동 일시정지 | P1 |
| FE-5 | 현재 재생 시간 표시 (MM:SS / 전체 MM:SS) | P1 |

### 3.3 프론트엔드: 하이라이트 타임라인

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| TL-1 | 프로그레스바 위에 하이라이트 구간을 컬러 마커로 표시 | P0 |
| TL-2 | 마커 클릭 시 해당 하이라이트 구간으로 점프 | P1 |
| TL-3 | 현재 재생 중인 하이라이트 마커 강조 (active 상태) | P1 |
| TL-4 | 마커 호버 시 하이라이트 제목 툴팁 표시 | P2 |

### 3.4 UI 통합

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| UI-1 | 분석 완료 시 하이라이트 그리드 위에 플레이어 표시 | P0 |
| UI-2 | HighlightCard의 Play 버튼 → `handlePlay()` → 플레이어 시크 연동 | P0 |
| UI-3 | 플레이어 닫기/최소화 기능 | P1 |
| UI-4 | 현재 재생 중인 하이라이트에 해당하는 HighlightCard 강조 | P2 |

## 4. 현재 코드 분석

### 수정 대상

| 파일 | 현재 동작 | 변경 필요 |
|------|----------|----------|
| `frontend/src/app/page.tsx` | `handlePlay()` = console.log + TODO | VideoPlayer에 시크 명령 전달 |
| `frontend/src/services/api.ts` | 영상 스트리밍 API 없음 | `getVideoStreamUrl()` 추가 |
| `frontend/src/types/index.ts` | Video 타입에 stream URL 없음 | 필요 시 타입 확장 |

### 신규 파일

| 파일 | 역할 |
|------|------|
| `backend/src/api/stream.py` | 영상 스트리밍 라우터 (Range Request 지원) |
| `frontend/src/components/organisms/VideoPlayer.tsx` | 영상 플레이어 + 컨트롤 |
| `frontend/src/components/molecules/HighlightTimeline.tsx` | 타임라인 하이라이트 마커 |

### 유지 부분 (변경 없음)

| 파일 | 이유 |
|------|------|
| `backend/src/services/video_processor.py` | AI 파이프라인 변경 없음 |
| `backend/src/services/export_processor.py` | Export 로직 변경 없음 |
| `backend/src/infrastructure/*` | DB 모델 변경 없음 |
| `frontend/src/components/molecules/HighlightCard.tsx` | onPlay 콜백 구조 유지 (내부 변경 최소) |

## 5. 영상 스트리밍 아키텍처

```
[Frontend VideoPlayer]
    │
    │  <video src="/api/videos/{id}/stream">
    │
    ▼
[Backend: GET /api/videos/{id}/stream]
    │
    ├─ Request Header: Range: bytes=0-1048575
    │
    ▼
[FileResponse / StreamingResponse]
    │
    ├─ Response: 206 Partial Content
    ├─ Content-Range: bytes 0-1048575/10485760
    └─ Content-Type: video/mp4
```

### Range Request 필요성
- 영상 파일이 수~수백 MB → 전체 다운로드 불가
- HTML5 `<video>`의 시크(seek) 기능에 필수
- `faststart` (moov atom at front) 이미 Export에서 적용 중

## 6. 플레이어 동작 흐름

```
[사용자: HighlightCard Play 클릭]
    │
    ▼
[handlePlay(highlight)]
    │
    ├─ videoPlayerRef.seekTo(highlight.startTime)
    ├─ videoPlayerRef.play()
    ├─ setActiveHighlight(highlight)
    │
    ▼
[VideoPlayer: 재생 중]
    │
    ├─ onTimeUpdate → 현재 시간 업데이트
    ├─ currentTime >= highlight.endTime → 자동 pause
    ├─ HighlightTimeline 마커 active 상태 반영
    │
    ▼
[사용자: 다른 하이라이트 클릭 또는 프로그레스바 시크]
```

## 7. 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| 영상 재생 | HTML5 `<video>` native | 외부 라이브러리 불필요, 간결 |
| Range Request | FastAPI StreamingResponse | `starlette.responses` 사용 |
| 상태 관리 | React useRef + useState | 플레이어 제어에 ref 필수 |
| 타임라인 | CSS absolute positioning | 하이라이트 구간을 %로 매핑 |

### 라이브러리 선택: Native HTML5 `<video>`
- **이유**: react-player, video.js 등 외부 라이브러리 불필요
  - 기본 컨트롤 + 커스텀 컨트롤만으로 충분
  - `currentTime`, `duration`, `seekTo` 등 native API 직접 사용
  - 번들 크기 증가 없음
  - 프로젝트 단순성 유지

## 8. 구현 범위

### In Scope
- 백엔드 영상 스트리밍 엔드포인트 (Range Request)
- HTML5 `<video>` 기반 플레이어 컴포넌트
- 기본 컨트롤 (Play/Pause, 볼륨, 프로그레스바)
- 하이라이트 클릭 → 자동 시크 + 구간 재생
- 타임라인 바에 하이라이트 마커 표시
- 하이라이트 종료 시점 자동 일시정지

### Out of Scope
- HLS/DASH 적응형 스트리밍 → v2 (대용량 영상용)
- 영상 품질 선택 (720p/1080p) → v2
- PIP (Picture-in-Picture) 모드 → 별도 feature
- 자막 오버레이 → subtitle-export feature
- 영상 프레임 썸네일 시크바 미리보기 → 별도 feature
- 키보드 단축키 (Space: play/pause 등) → 별도 enhancement

## 9. 수정 대상 파일 요약

| 파일 | 변경 유형 | 변경 내용 |
|------|----------|----------|
| `backend/src/api/stream.py` | **신규** | 영상 스트리밍 라우터 (Range Request) |
| `backend/src/main.py` | 수정 | stream 라우터 등록 |
| `frontend/src/components/organisms/VideoPlayer.tsx` | **신규** | HTML5 영상 플레이어 + 커스텀 컨트롤 |
| `frontend/src/components/molecules/HighlightTimeline.tsx` | **신규** | 프로그레스바 하이라이트 마커 |
| `frontend/src/app/page.tsx` | 수정 | VideoPlayer 통합, handlePlay 구현 |
| `frontend/src/services/api.ts` | 수정 | getVideoStreamUrl() 추가 |

## 10. 리스크

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| 대용량 영상 (>1GB) 스트리밍 지연 | 버퍼링 빈번 | Range Request로 부분 로딩 |
| 비-MP4 파일 (mov, mkv 등) 브라우저 미지원 | 재생 불가 | MP4만 지원 안내 또는 트랜스코딩 |
| CORS 문제 (영상 스트림) | 로드 실패 | 백엔드에 CORS 헤더 설정 |
| 모바일 autoplay 정책 | 자동 재생 차단 | muted 시작 후 unmute 또는 사용자 인터랙션 후 재생 |
| 메모리 사용량 (긴 영상) | 브라우저 메모리 부족 | 스트리밍 + Range Request로 최소화 |

## 11. 성공 기준

| 기준 | 목표 |
|------|------|
| 하이라이트 미리보기 | Play 클릭 → 해당 구간 즉시 재생 |
| 시크 응답 시간 | 프로그레스바/마커 클릭 → 1초 이내 재생 시작 |
| 타임라인 정확도 | 마커 위치가 실제 하이라이트 시간과 정확히 일치 |
| 자동 정지 | 하이라이트 종료 시점에 정확히 일시정지 |
| 브라우저 호환 | Chrome, Safari, Firefox에서 정상 재생 |
