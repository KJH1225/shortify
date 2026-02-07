# Shortify API Specification

> Version: 0.1.0
> Base URL: `http://localhost:8000`

---

## Overview

Shortify API는 AI 기반 영상 하이라이트 추출 서비스의 백엔드 API입니다.

### Authentication

현재 버전에서는 인증이 필요하지 않습니다. (향후 JWT 기반 인증 추가 예정)

### Rate Limiting

- **제한**: 60 requests / 60 seconds (IP 기준)
- **응답**: `429 Too Many Requests`

### Response Format

**성공 응답**:
```json
{
  "data": { ... },
  "meta": { ... }  // optional
}
```

**에러 응답**:
```json
{
  "detail": "에러 메시지"
}
```

---

## Endpoints

### Videos

#### POST /api/videos/upload

영상 파일 업로드 및 분석 시작

**Request**:
- Content-Type: `multipart/form-data`
- Body:
  | Field | Type | Required | Description |
  |-------|------|:--------:|-------------|
  | file | File | Yes | 영상 파일 (.mp4, .mov, .avi, .mkv, .webm, .m4v) |

**Validation**:
- 허용 확장자: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.m4v`
- 허용 MIME 타입: `video/mp4`, `video/quicktime`, `video/x-msvideo`, `video/x-matroska`, `video/webm`, `video/x-m4v`
- 최대 파일 크기: 2GB

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "title": "filename.mp4",
  "source": {
    "type": "file",
    "filename": "filename.mp4"
  },
  "duration": null,
  "status": "uploading",
  "progress": 0,
  "message": "업로드 중...",
  "highlights": [],
  "created_at": "2026-02-08T00:00:00Z",
  "updated_at": "2026-02-08T00:00:00Z"
}
```

**Errors**:
- `400 Bad Request`: 지원하지 않는 파일 형식 또는 크기 초과

---

#### POST /api/videos/youtube

YouTube URL로 분석 시작

**Request**:
- Content-Type: `application/json`
- Body:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }
  ```

**Validation**:
- 허용 URL 패턴:
  - `youtube.com/watch?v=`
  - `youtu.be/`
  - `youtube.com/embed/`
  - `youtube.com/v/`
  - `youtube.com/shorts/`

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "title": "YouTube: VIDEO_ID",
  "source": {
    "type": "youtube",
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
  },
  "duration": null,
  "status": "processing",
  "progress": 0,
  "message": "YouTube 영상 정보 가져오는 중...",
  "highlights": [],
  "created_at": "2026-02-08T00:00:00Z",
  "updated_at": "2026-02-08T00:00:00Z"
}
```

**Errors**:
- `400 Bad Request`: 유효하지 않은 YouTube URL

---

#### GET /api/videos/{video_id}

영상 정보 및 처리 상태 조회

**Parameters**:
| Name | Type | Location | Description |
|------|------|----------|-------------|
| video_id | string | path | 영상 UUID |

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "title": "Video Title",
  "source": {
    "type": "file|youtube",
    "filename": "...",
    "url": "..."
  },
  "duration": 120.5,
  "status": "idle|uploading|processing|completed|error",
  "progress": 100,
  "message": "처리 완료",
  "highlights": [
    {
      "id": "highlight-uuid",
      "video_id": "video-uuid",
      "start_time": 45.0,
      "end_time": 78.0,
      "title": "핵심 개념 설명",
      "description": "...",
      "score": 0.95,
      "thumbnail_url": "...",
      "created_at": "2026-02-08T00:00:00Z"
    }
  ],
  "created_at": "2026-02-08T00:00:00Z",
  "updated_at": "2026-02-08T00:00:00Z"
}
```

**Errors**:
- `404 Not Found`: 영상을 찾을 수 없음

---

#### GET /api/videos/

모든 영상 목록 조회

**Response** (200 OK):
```json
[
  {
    "id": "uuid-string",
    "title": "Video Title",
    ...
  }
]
```

---

#### DELETE /api/videos/{video_id}

영상 삭제

**Response** (200 OK):
```json
{
  "data": {
    "success": true,
    "message": "삭제되었습니다"
  }
}
```

**Errors**:
- `404 Not Found`: 영상을 찾을 수 없음

---

### Highlights

#### GET /api/highlights/{highlight_id}

하이라이트 상세 조회

**Response** (200 OK):
```json
{
  "id": "highlight-uuid",
  "video_id": "video-uuid",
  "start_time": 45.0,
  "end_time": 78.0,
  "title": "핵심 개념 설명",
  "description": "주요 개념에 대한 상세 설명이 포함된 구간",
  "score": 0.95,
  "thumbnail_url": "https://...",
  "created_at": "2026-02-08T00:00:00Z"
}
```

**Errors**:
- `404 Not Found`: 하이라이트를 찾을 수 없음

---

#### POST /api/highlights/{highlight_id}/export

하이라이트를 숏폼 영상으로 내보내기

**Response** (200 OK):
```json
{
  "data": {
    "success": true,
    "message": "Export job created",
    "export_id": "export_highlight-uuid",
    "status": "processing",
    "estimated_time": 30
  }
}
```

**Errors**:
- `404 Not Found`: 하이라이트를 찾을 수 없음

---

#### DELETE /api/highlights/{highlight_id}

하이라이트 삭제

**Response** (200 OK):
```json
{
  "data": {
    "success": true,
    "message": "Highlight deleted"
  }
}
```

**Errors**:
- `404 Not Found`: 하이라이트를 찾을 수 없음

---

### Health

#### GET /health

서버 상태 확인

**Response** (200 OK):
```json
{
  "status": "healthy"
}
```

---

## Processing Status Flow

```
idle → uploading → processing → completed
                       ↓
                     error
```

| Status | Description |
|--------|-------------|
| `idle` | 초기 상태 |
| `uploading` | 파일 업로드 중 |
| `processing` | AI 분석 중 |
| `completed` | 처리 완료 |
| `error` | 오류 발생 |

---

## Error Codes

| HTTP Status | Description |
|:-----------:|-------------|
| 400 | Bad Request - 잘못된 요청 (파일 형식, URL 형식 등) |
| 404 | Not Found - 리소스를 찾을 수 없음 |
| 429 | Too Many Requests - Rate Limit 초과 |
| 500 | Internal Server Error - 서버 내부 오류 |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-08 | Initial API specification |
