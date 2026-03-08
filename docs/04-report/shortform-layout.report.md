# PDCA Completion Report: shortform-layout

> **Feature**: Export 시 원본/숏폼(9:16) 레이아웃 선택 + FFmpeg 세이프존 적용
>
> **Project**: Shortify
> **Level**: Dynamic
> **Report Date**: 2026-03-08
> **Status**: COMPLETED

---

## 1. Executive Summary

### 1.1 Key Metrics

| Metric | Result |
|--------|--------|
| **Design Match Rate** | 100% |
| **Iterations Required** | 0 |
| **Verification Items** | 13/13 PASS |
| **Files Modified** | 8 |
| **New Dependencies** | 0 |

### 1.2 Project Overview

| Item | Value |
|------|-------|
| Feature | shortform-layout |
| Started | 2026-03-08 |
| Completed | 2026-03-08 |
| PDCA Phases | Plan → Design → Do → Check → Report |

### 1.3 Value Delivered

| Perspective | Result |
|-------------|--------|
| **Problem** | 기존 Export는 원본 비율 클리핑만 수행하여 숏폼 플랫폼에서 가로/정방형 영상이 최적화되지 않았음. 별도 편집 앱이 필요했음 |
| **Solution** | Export API에 `layout` 파라미터 추가 (original/shortform). 숏폼 모드는 FFmpeg filter_complex로 9:16 캔버스 + 세이프존 + 블러 배경을 자동 적용 |
| **Function/UX Effect** | HighlightCard에 "원본" / "숏폼 9:16" 두 버튼이 표시되어, 용도에 맞는 Export를 한 번에 선택 가능. 기존 동작은 100% 하위 호환 |
| **Core Value** | "추출에서 업로드까지 원스톱" — 편집기 없이 숏폼 플랫폼에 바로 올릴 수 있는 영상 완성본 제공. 사용자 워크플로우에서 편집 단계 제거 |

---

## 2. PDCA Cycle Summary

### 2.1 Plan Phase

**Document**: `docs/01-plan/features/shortform-layout.plan.md`

- 10개 기능 요구사항 정의 (FR-01 ~ FR-10)
- 레이아웃 선택형 설계 결정 (original/shortform)
- 기본값 `original`로 하위 호환 보장
- 세이프존 수치 확정: 상단 15%(288px) / 하단 35%(672px) / 콘텐츠 960px

### 2.2 Design Phase

**Document**: `docs/02-design/features/shortform-layout.design.md`

- 변경 대상 8개 파일 식별 (Backend 4 + Frontend 4)
- FFmpeg 필터 체인 상세 설계 (portrait/landscape 분기)
- API 인터페이스 설계 (`ExportRequest` Pydantic 모델)
- Frontend UI 설계 (hover overlay → 카드 하단 버튼 2개)
- 13개 Verification Items 정의

### 2.3 Do Phase

**Modified Files** (8):

| # | File | Change |
|---|------|--------|
| 1 | `backend/src/core/constants.py` | `SHORTFORM_*` 상수 7개 추가 |
| 2 | `backend/src/models/schemas.py` | `ExportLayout` enum + `ExportRequest` 모델 |
| 3 | `backend/src/services/export_processor.py` | `layout` 필드, `_get_video_dimensions()`, `_build_shortform_cmd()`, `process_export` 분기 |
| 4 | `backend/src/api/highlights.py` | `ExportRequest` body 파라미터 + `layout` 전달 |
| 5 | `frontend/src/services/api.ts` | `export(id, layout)` + JSON body |
| 6 | `frontend/src/components/molecules/HighlightCard.tsx` | "원본" / "숏폼 9:16" 버튼 2개 |
| 7 | `frontend/src/components/organisms/HighlightGrid.tsx` | `onExport` prop 타입 변경 |
| 8 | `frontend/src/app/page.tsx` | `handleExport(highlight, layout)` 시그니처 |

### 2.4 Check Phase

**Document**: `docs/03-analysis/shortform-layout.analysis.md`

- Match Rate: **100%** (13/13 PASS)
- Gap: 0건
- 구현이 Design 대비 추가한 개선: 출력 파일명 `_sf` 접미사 (충돌 방지)

---

## 3. Technical Details

### 3.1 Backend Architecture

```
POST /api/highlights/{id}/export
  body: { layout: "original" | "shortform" }
    │
    ├─ layout=original → 기존 FFmpeg 클리핑 (변경 없음)
    │
    └─ layout=shortform
        ├─ ffprobe → 원본 width/height 감지
        ├─ portrait? → scale + pad (1080x1920)
        └─ landscape/square?
            ├─ [bg] 원본 → scale 1080x1920 → boxblur 20:20
            ├─ [fg] 원본 → fit 1080x960
            └─ overlay → fg on bg at y=288+(960-h)/2
```

### 3.2 Frontend UX

```
HighlightCard (Before)          HighlightCard (After)
┌──────────────────┐            ┌──────────────────┐
│ [Thumbnail]      │            │ [Thumbnail]      │
│ hover: Play+DL   │            │ hover: Play only │
├──────────────────┤            ├──────────────────┤
│ Title            │            │ Title            │
│ Description      │            │ Description      │
│ Time    Score    │            │ Time    Score    │
└──────────────────┘            │ [원본] [숏폼9:16]│
                                └──────────────────┘
```

### 3.3 Backward Compatibility

- `layout` 파라미터 기본값: `"original"`
- body 없이 POST → `ExportRequest()` 기본값 적용 → 기존 동작 그대로
- 기존 프론트엔드에서 API 호출해도 문제 없음

---

## 4. Verification Results

| ID | Verification | Result |
|----|-------------|:------:|
| V-01 | body 없이 POST → original | PASS |
| V-02 | layout=original → 원본 클리핑 | PASS |
| V-03 | layout=shortform → 1080x1920 | PASS |
| V-04 | 가로 + shortform → blur+safezone | PASS |
| V-05 | 정방형 + shortform → blur+safezone | PASS |
| V-06 | 세로 + shortform → resize | PASS |
| V-07 | ffprobe 비율 감지 | PASS |
| V-08 | 원본/숏폼 버튼 렌더링 | PASS |
| V-09 | "원본" → layout=original 전달 | PASS |
| V-10 | "숏폼 9:16" → layout=shortform 전달 | PASS |
| V-11 | Redis layout 저장/복원 | PASS |
| V-12 | H.264/AAC/faststart 호환성 | PASS |
| V-13 | 오디오 싱크 유지 | PASS |

---

## 5. PDCA Documents

| Phase | Document |
|-------|----------|
| Plan | `docs/01-plan/features/shortform-layout.plan.md` |
| Design | `docs/02-design/features/shortform-layout.design.md` |
| Analysis | `docs/03-analysis/shortform-layout.analysis.md` |
| Report | `docs/04-report/shortform-layout.report.md` |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-03-08 | Completion report | Claude |
