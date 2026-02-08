# Design: highlight-download

> Feature: 하이라이트 클립 다운로드 기능 완성
> Plan: `docs/01-plan/features/highlight-download.plan.md`
> Created: 2026-02-08

## 1. 구현 순서

```
1. [BE] highlights.py - 다운로드 엔드포인트 추가
2. [BE] export_processor.py - get_job_status에 download_url 필드 추가
3. [FE] api.ts - getExportStatus, downloadExport 메서드 추가
4. [FE] page.tsx - handleExport 로직 (폴링 → 자동 다운로드)
```

## 2. Backend 설계

### 2.1 다운로드 엔드포인트

**파일**: `backend/src/api/highlights.py`

```
GET /api/highlights/{highlight_id}/export/{export_id}/download
```

**로직**:
1. `export_processor.get_job(export_id)`로 Job 조회
2. Job이 없으면 → 404 `EXPORT_JOB_NOT_FOUND`
3. Job status가 `completed`가 아니면 → 409 `EXPORT_NOT_READY`
4. `job.output_path` 파일 존재 여부 확인
5. 파일 없으면 → 404 `EXPORT_FILE_NOT_FOUND`
6. `FileResponse`로 파일 반환

**응답 헤더**:
```
Content-Type: video/mp4
Content-Disposition: attachment; filename="highlight_{highlight_id}.mp4"
```

**에러 응답**:

| 상황 | Status | Code |
|------|--------|------|
| Job 없음 | 404 | `EXPORT_JOB_NOT_FOUND` |
| Export 미완료/진행중 | 409 | `EXPORT_NOT_READY` |
| 생성된 파일 없음 | 404 | `EXPORT_FILE_NOT_FOUND` |

### 2.2 상태 조회 응답 개선

**파일**: `backend/src/services/export_processor.py` - `get_job_status()`

`status == completed`일 때 `download_url` 필드 추가:

```python
{
    "export_id": "export_abc123",
    "highlight_id": "...",
    "status": "completed",
    "download_url": "/api/highlights/{highlight_id}/export/{export_id}/download",
    # ... 기존 필드
}
```

## 3. Frontend 설계

### 3.1 API 클라이언트 추가

**파일**: `frontend/src/services/api.ts`

`highlightApi`에 2개 메서드 추가:

```typescript
// Export 상태 조회
getExportStatus: async (highlightId: string, exportId: string): Promise<ApiResponse<ExportStatusResponse>>

// 다운로드 (브라우저 파일 저장 트리거)
downloadExport: async (highlightId: string, exportId: string): Promise<void>
```

**ExportStatusResponse 타입 추가**:

```typescript
interface ExportStatusResponse {
  export_id: string;
  highlight_id: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  download_url: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}
```

**downloadExport 구현 방식**:
- `window.open(url)` 또는 `<a>` 태그 동적 생성으로 브라우저 다운로드 트리거
- Blob 다운로드 불필요 (FileResponse가 Content-Disposition: attachment 반환)

### 3.2 handleExport 로직 개선

**파일**: `frontend/src/app/page.tsx`

현재 `handleExport`:
```
클릭 → export 시작 → alert("Job ID: ...") → 끝
```

변경 후 `handleExport`:
```
클릭 → export 시작 → 폴링 시작 (1초 간격)
      → pending/processing: 대기
      → completed: 다운로드 트리거 + 성공 알림
      → error: 에러 메시지 표시
      → 최대 60초 timeout
```

**상태 관리**:
- `exportingHighlightId: string | null` 상태 추가
- 특정 하이라이트가 export 중일 때 해당 카드에 로딩 표시
- 다중 export 동시 실행 방지

### 3.3 HighlightCard UI 변경

**파일**: `frontend/src/components/molecules/HighlightCard.tsx`

- props에 `isExporting: boolean` 추가
- `isExporting=true`일 때 Download 버튼 → 로딩 스피너로 변경
- 버튼 disabled 처리

## 4. 시퀀스 다이어그램

```
User          Frontend              Backend            FFmpeg
 |               |                     |                  |
 |--[Download]-->|                     |                  |
 |               |--POST /export------>|                  |
 |               |<--{export_id}-------|                  |
 |               |                     |--process_export->|
 |               |--GET /status------->|                  |
 |               |<--{status:process}--|                  |
 |               |       ...           |                  |
 |               |--GET /status------->|<--clip.mp4-------|
 |               |<--{status:complete}-|                  |
 |               |                     |                  |
 |               |--GET /download----->|                  |
 |               |<--[mp4 file]--------|                  |
 |<-[save file]--|                     |                  |
```

## 5. 검증 항목

| ID | 검증 항목 | 방법 |
|----|----------|------|
| V-1 | 다운로드 엔드포인트가 FileResponse를 반환하는지 | curl 테스트 |
| V-2 | 미완료 Export에 409 반환하는지 | status=processing 상태에서 download 호출 |
| V-3 | 존재하지 않는 Job에 404 반환하는지 | 잘못된 export_id로 호출 |
| V-4 | FE에서 폴링 후 자동 다운로드 되는지 | 브라우저 테스트 |
| V-5 | Export 중 로딩 UI가 표시되는지 | 브라우저 테스트 |
| V-6 | 에러 시 사용자에게 메시지 표시하는지 | FFmpeg 없는 환경 테스트 |
| V-7 | 상태 조회에 download_url 포함되는지 | API 응답 확인 |
