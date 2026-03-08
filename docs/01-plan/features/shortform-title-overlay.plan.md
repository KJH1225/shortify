# Plan: Shortform Title Overlay

## Executive Summary

| Item | Detail |
|------|--------|
| Feature | shortform-title-overlay |
| Created | 2026-03-09 |
| Phase | Plan |

### Value Delivered

| Perspective | Description |
|-------------|-------------|
| Problem | 숏폼 내보내기 영상에 제목이 없어서 어떤 내용의 클립인지 시각적으로 알 수 없음 |
| Solution | FFmpeg drawtext 필터로 하이라이트 제목을 영상 상단 safe zone에 오버레이 |
| Function UX Effect | 내보낸 숏폼 영상 상단에 굵은 제목 텍스트가 자동 표시되어 콘텐츠 식별성 향상 |
| Core Value | SNS 업로드 시 별도 편집 없이 바로 사용 가능한 완성도 높은 숏폼 클립 생성 |

---

## 1. Feature Overview

스크린샷 레퍼런스처럼, 숏폼(9:16) 내보내기 시 영상 상단 영역에 하이라이트 제목 텍스트를 오버레이하는 기능.

### 현재 상태
- 숏폼 레이아웃은 구현 완료 (1080x1920, blur 배경 + 중앙 콘텐츠)
- 하이라이트 title은 DB에 저장됨 (최대 20자)
- **ExportJob에 title이 전달되지 않음** → 영상에 텍스트 오버레이 없음

### 목표
- 숏폼 내보내기 시 영상 상단(safe zone, y=288 기준 위쪽)에 제목 텍스트 표시
- 흰색 또는 노란색 굵은 폰트, 그림자 효과로 가독성 확보
- 기존 original 레이아웃에는 영향 없음

---

## 2. Implementation Scope

### 2.1 Backend Changes

#### A. ExportRequest / ExportJob에 title 전달
- **`models/schemas.py`**: `ExportRequest`에 `title: str | None = None` 필드 추가
- **`services/export_processor.py`**: `ExportJob`에 `title` 필드 추가, `create_export_job()`에 title 파라미터 추가
- **`api/highlights.py`**: export 엔드포인트에서 `highlight.title`을 `create_export_job()`에 전달

#### B. FFmpeg drawtext 필터 추가
- **`services/export_processor.py`**:
  - `_build_shortform_cmd()`: 단일 클립 숏폼에 drawtext 필터 추가
  - `_build_shortform_concat_cmd()`: 멀티 클립 숏폼에 drawtext 필터 추가
- **drawtext 스펙**:
  - 위치: 상단 safe zone 중앙 (`x=(w-text_w)/2`, `y=100~150`)
  - 폰트: 시스템 한글 폰트 (Apple SD Gothic Neo Bold 또는 설정 가능)
  - 크기: 48~56px
  - 색상: 흰색 (`#FFFFFF`), 테두리/그림자로 가독성 확보
  - borderw=3, shadowcolor=black, shadowx=2, shadowy=2

#### C. Constants 추가
- **`core/constants.py`**: 제목 오버레이 관련 상수
  - `SHORTFORM_TITLE_FONTSIZE = 52`
  - `SHORTFORM_TITLE_Y = 130` (safe zone 내부)
  - `SHORTFORM_TITLE_FONTCOLOR = "white"`
  - `SHORTFORM_TITLE_BORDERW = 3`

### 2.2 Frontend Changes (없음 또는 최소)
- `ExportRequest`에 title은 백엔드에서 DB 조회하여 자동 전달하므로 프론트 변경 불필요
- API 호출 시 `{ layout }` 만 보내면 백엔드가 highlight.title을 자동으로 사용

---

## 3. Implementation Order

1. `core/constants.py` — 제목 오버레이 상수 추가
2. `models/schemas.py` — ExportRequest에 title 필드 추가 (optional)
3. `services/export_processor.py` — ExportJob에 title 추가 + drawtext 필터 구현
4. `api/highlights.py` — title을 export job에 전달
5. 테스트 — 실제 숏폼 내보내기로 제목 표시 확인

---

## 4. Technical Details

### FFmpeg drawtext 필터 예시

```
drawtext=text='하이라이트 제목':fontfile=/System/Library/Fonts/AppleSDGothicNeo.ttc:fontsize=52:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=130:shadowcolor=black@0.5:shadowx=2:shadowy=2
```

### 폰트 전략
- macOS: `/System/Library/Fonts/AppleSDGothicNeo.ttc` (시스템 내장)
- Linux/Docker: NanumGothic 또는 Noto Sans CJK 설치 필요
- 설정 가능한 `SHORTFORM_TITLE_FONT` 상수로 환경별 대응

### filter_complex 통합 방식
- 기존 shortform 필터 체인 마지막에 drawtext 추가
- 예: `...,setsar=1,drawtext=...[outv]` (기존 `[outv]` 라벨 앞에 삽입)

---

## 5. Risk & Considerations

| Risk | Mitigation |
|------|-----------|
| 한글 폰트 미설치 환경 | fontfile 미지정 시 기본 폰트 fallback, 에러 시 텍스트 없이 진행 |
| 긴 제목 텍스트 잘림 | 하이라이트 title은 20자 제한이므로 1080px 폭에 충분히 수용 |
| 특수문자 escape | FFmpeg drawtext에서 `'`, `:`, `\` 등 이스케이프 처리 필요 |
| 성능 영향 | drawtext는 가벼운 필터, 인코딩 시간에 유의미한 영향 없음 |

---

## 6. Affected Files

| File | Change |
|------|--------|
| `backend/src/core/constants.py` | 제목 오버레이 상수 추가 |
| `backend/src/models/schemas.py` | ExportRequest에 title 필드 (optional) |
| `backend/src/services/export_processor.py` | ExportJob title 필드 + drawtext 필터 |
| `backend/src/api/highlights.py` | highlight.title → export job 전달 |
