# Plan: video-history

> Feature: 영상 히스토리 & 관리 — 과거 분석된 영상 목록 조회, 재열기, 삭제
> Created: 2026-02-09
> Level: Dynamic

## 1. 배경

현재 Shortify는 **단일 세션 기반** — 영상을 업로드하고 결과를 보면 끝:
- Header에 `히스토리` 버튼이 있지만 **동작하지 않음** (Header.tsx:13)
- 백엔드에 `GET /api/videos/` (목록), `DELETE /api/videos/{id}` (삭제) API가 **이미 존재**
- 프론트엔드에서 이 API를 호출하지 않음 — UI가 없음
- 이전에 분석한 영상의 하이라이트를 **다시 볼 수 없음**
- 페이지를 새로고침하면 모든 상태가 초기화됨

## 2. 목표

이전에 분석한 영상을 **히스토리 페이지에서 다시 열어** 하이라이트를 확인하고, 플레이어로 재생하며, 불필요한 영상을 삭제할 수 있게 한다.

### 핵심 가치
- Header `히스토리` 버튼 클릭 → 과거 영상 목록 표시
- 영상 카드 클릭 → 해당 영상의 하이라이트 + VideoPlayer 재열기
- 삭제 버튼으로 영상 + 하이라이트 정리
- 처리 상태별 표시 (완료/처리중/에러)

## 3. 요구사항

### 3.1 프론트엔드: 히스토리 페이지

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FE-1 | `/history` 라우트에 히스토리 페이지 생성 | P0 |
| FE-2 | `GET /api/videos/` 호출하여 영상 목록 표시 | P0 |
| FE-3 | 영상 카드: 제목, 소스(YouTube/파일), 상태, 하이라이트 수, 생성일시 | P0 |
| FE-4 | 영상 카드 클릭 → 메인 페이지로 이동 + 해당 영상 하이라이트 로드 | P0 |
| FE-5 | 삭제 버튼 + 확인 다이얼로그 → `DELETE /api/videos/{id}` 호출 | P1 |
| FE-6 | 처리 상태별 배지 표시 (completed: 녹색, processing: 노란색, error: 빨간색) | P1 |
| FE-7 | 빈 상태 표시 (영상이 없을 때 안내 메시지) | P1 |
| FE-8 | 최신순 정렬 (기본) | P1 |

### 3.2 프론트엔드: 네비게이션 연동

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| NAV-1 | Header `히스토리` 버튼 → `/history` 이동 | P0 |
| NAV-2 | 메인 페이지에서 영상 ID 기반 하이라이트 로드 기능 (URL 파라미터 또는 store) | P0 |
| NAV-3 | 히스토리에서 영상 선택 시 메인 페이지의 VideoPlayer까지 연동 | P0 |

### 3.3 프론트엔드: API 클라이언트

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| API-1 | `videoApi.getAll()` — 이미 존재, 그대로 사용 | P0 |
| API-2 | `videoApi.delete()` — 이미 존재, 그대로 사용 | P1 |

### 3.4 백엔드

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| BE-1 | `GET /api/videos/` — **이미 구현됨** (videos.py:150) | ✅ 완료 |
| BE-2 | `DELETE /api/videos/{id}` — **이미 구현됨** (videos.py:158) | ✅ 완료 |
| BE-3 | 업로드 파일도 함께 삭제 (현재 DB만 삭제, 파일 미삭제) | P2 |

## 4. 현재 코드 분석

### 이미 완성된 부분 (변경 불필요)

| 파일 | 내용 |
|------|------|
| `backend/src/api/videos.py:150-155` | `GET /api/videos/` — 전체 영상 목록 (created_at DESC) |
| `backend/src/api/videos.py:158-174` | `DELETE /api/videos/{id}` — 영상 + 하이라이트 삭제 |
| `backend/src/infrastructure/repository.py:46-53` | `list_all()` — selectinload(highlights) 포함 |
| `frontend/src/services/api.ts` | `videoApi.getAll()`, `videoApi.delete()` 이미 존재 |

### 수정 대상

| 파일 | 현재 동작 | 변경 필요 |
|------|----------|----------|
| `frontend/src/components/organisms/Header.tsx` | 히스토리 버튼 비활성 | Link로 `/history` 이동 |
| `frontend/src/app/page.tsx` | URL 파라미터 미지원 | videoId 쿼리 파라미터로 하이라이트 로드 |

### 신규 파일

| 파일 | 역할 |
|------|------|
| `frontend/src/app/history/page.tsx` | 히스토리 페이지 |
| `frontend/src/components/molecules/VideoHistoryCard.tsx` | 영상 히스토리 카드 컴포넌트 |

## 5. 페이지 흐름

```
[Header: 히스토리 클릭]
    │
    ▼
[/history 페이지]
    │
    ├── GET /api/videos/ → 영상 목록 로드
    │
    ├── VideoHistoryCard 그리드 표시
    │     ├── 제목, 소스 타입, 상태 배지
    │     ├── 하이라이트 N개, 생성일시
    │     ├── [열기] 버튼 → /?videoId={id} 이동
    │     └── [삭제] 버튼 → 확인 → DELETE API
    │
    ▼
[메인 페이지: /?videoId=6]
    │
    ├── useSearchParams로 videoId 추출
    ├── GET /api/videos/{videoId} → 영상 정보 + 하이라이트 로드
    ├── setCurrentVideoId, setHighlights, setStatus
    │
    ▼
[하이라이트 그리드 + VideoPlayer 사용 가능]
```

## 6. 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| 라우팅 | Next.js App Router | `/history` 디렉토리 기반 |
| 네비게이션 | `next/link` | Header 히스토리 버튼 |
| URL 파라미터 | `useSearchParams` | 메인 페이지 videoId 로드 |
| 상태 관리 | 기존 Zustand store | `useVideoStore` 재사용 |
| API 클라이언트 | 기존 `videoApi` | `getAll()`, `delete()` 재사용 |

## 7. 구현 범위

### In Scope
- `/history` 페이지 + VideoHistoryCard 컴포넌트
- Header 히스토리 버튼 → Link 연동
- 메인 페이지 URL 파라미터(`?videoId=N`) 기반 영상 로드
- 영상 삭제 + 확인 다이얼로그
- 상태별 배지 (completed/processing/error)

### Out of Scope
- 검색/필터 기능 → 별도 feature
- 페이지네이션/무한 스크롤 → 별도 feature (현재 전체 로드)
- 업로드 파일 물리 삭제 → P2 (현재 DB만 삭제)
- 영상 목록 정렬 옵션 → 별도 enhancement

## 8. 수정 대상 파일 요약

| 파일 | 변경 유형 | 변경 내용 |
|------|----------|----------|
| `frontend/src/app/history/page.tsx` | **신규** | 히스토리 페이지 |
| `frontend/src/components/molecules/VideoHistoryCard.tsx` | **신규** | 영상 히스토리 카드 |
| `frontend/src/components/organisms/Header.tsx` | 수정 | 히스토리 Link 연동 |
| `frontend/src/app/page.tsx` | 수정 | ?videoId 쿼리 파라미터 지원 |

## 9. 리스크

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| 영상 목록이 많아질 때 성능 | 느린 로딩 | 현재 규모에선 문제 없음, 추후 페이지네이션 |
| 삭제 시 파일 미삭제 | 디스크 공간 낭비 | P2로 별도 처리, DB 삭제만 우선 |
| 메인 페이지 새로고침 시 videoId 유실 | UX 문제 없음 | URL 파라미터 유지 |

## 10. 성공 기준

| 기준 | 목표 |
|------|------|
| 히스토리 접근 | Header 버튼 → /history 페이지 즉시 이동 |
| 영상 목록 | 과거 분석 영상이 최신순으로 전부 표시 |
| 영상 재열기 | 카드 클릭 → 메인 페이지에서 하이라이트 + 플레이어 정상 동작 |
| 영상 삭제 | 삭제 → 확인 → 목록에서 즉시 제거 |
| 상태 표시 | completed/processing/error 배지가 올바르게 표시 |
