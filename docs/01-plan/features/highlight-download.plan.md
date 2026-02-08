# Plan: highlight-download

> Feature: 하이라이트 클립 다운로드 기능 완성
> Created: 2026-02-08
> Level: Dynamic

## 1. 배경

하이라이트 Export 기능이 **부분 구현** 상태:
- BE: FFmpeg 클리핑 (`export_processor.py`) + Export 상태 조회 API 구현됨
- BE: **생성된 파일을 클라이언트에 전달하는 다운로드 엔드포인트 없음**
- FE: Export API 호출 (`highlightApi.export()`) 구현됨
- FE: **Export 완료 후 실제 파일 다운로드 로직 없음** (alert만 표시)

## 2. 목표

Export 완료된 하이라이트 클립을 클라이언트에서 다운로드할 수 있도록 **End-to-End 파이프라인 완성**

## 3. 요구사항

### 3.1 Backend

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| BE-1 | `GET /api/highlights/{highlight_id}/export/{export_id}/download` 엔드포인트 추가 | P0 |
| BE-2 | FileResponse로 생성된 mp4 파일 반환 (Content-Disposition: attachment) | P0 |
| BE-3 | Export 미완료/실패 시 적절한 에러 응답 (404/409) | P0 |
| BE-4 | export 상태 조회 응답에 `download_url` 필드 추가 | P1 |

### 3.2 Frontend

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FE-1 | `highlightApi`에 `download(highlightId, exportId)` 메서드 추가 | P0 |
| FE-2 | Export 버튼 클릭 → Export 시작 → 폴링으로 완료 대기 → 자동 다운로드 | P0 |
| FE-3 | Export 진행 상태를 UI에 표시 (로딩 스피너 또는 진행률) | P1 |
| FE-4 | 에러 핸들링 (FFmpeg 미설치, 원본 파일 없음 등) | P1 |

## 4. 현재 코드 분석

### 이미 구현된 부분 (재사용)
- `export_processor.py`: FFmpeg 클리핑, ExportJob 관리, 상태 조회
- `highlights.py`: `POST /{highlight_id}/export`, `GET /{highlight_id}/export/{export_id}/status`
- `api.ts`: `highlightApi.export()`, `ExportResponse` 타입
- `HighlightCard.tsx`: Download 버튼 UI, `onExport` 콜백

### 추가 구현 필요
- `highlights.py`: 다운로드 엔드포인트 1개
- `api.ts`: 다운로드 + 폴링 메서드 2개
- `page.tsx`: `handleExport` 로직 개선

## 5. 구현 범위

### In Scope
- 다운로드 API 엔드포인트
- FE 다운로드 트리거 (브라우저 파일 저장)
- Export 상태 폴링 → 완료 시 자동 다운로드
- 기본 에러 핸들링

### Out of Scope
- 비디오 스트리밍/재생 (별도 feature: `video-playback`)
- Redis 기반 Job 영속화 (현재 in-memory 유지)
- YouTube 영상 다운로드 (저작권 이슈)
- 다중 하이라이트 일괄 다운로드

## 6. 기술 스택

| 영역 | 기술 |
|------|------|
| BE 파일 반환 | FastAPI `FileResponse` |
| FE 다운로드 | `window.URL.createObjectURL` + `<a>` 태그 트리거 |
| FE 폴링 | `setInterval` + export status API |

## 7. 수정 대상 파일 (예상)

| 파일 | 변경 내용 |
|------|----------|
| `backend/src/api/highlights.py` | 다운로드 엔드포인트 추가 |
| `frontend/src/services/api.ts` | download, pollExportStatus 메서드 추가 |
| `frontend/src/app/page.tsx` | handleExport 로직 개선 |

## 8. 리스크

| 리스크 | 완화 방안 |
|--------|----------|
| Export가 in-memory 저장 → 서버 재시작 시 job 유실 | MVP 단계에서 허용, 추후 DB 저장으로 전환 |
| FFmpeg 미설치 환경 | 에러 메시지로 안내 |
| 대용량 파일 다운로드 | Content-Length 헤더 설정, 스트리밍 응답 고려 |
