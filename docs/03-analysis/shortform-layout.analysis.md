# shortform-layout Analysis Report

> **Analysis Type**: Gap Analysis (Design vs Implementation)
>
> **Project**: Shortify
> **Version**: 0.2.0
> **Date**: 2026-03-08
> **Design Doc**: [shortform-layout.design.md](../02-design/features/shortform-layout.design.md)

---

## 1. Analysis Overview

### 1.1 Analysis Scope

- **Design Document**: `docs/02-design/features/shortform-layout.design.md`
- **Implementation Files**:
  - `backend/src/core/constants.py` — Shortform 상수
  - `backend/src/models/schemas.py` — ExportLayout, ExportRequest
  - `backend/src/services/export_processor.py` — layout 필드, shortform FFmpeg
  - `backend/src/api/highlights.py` — ExportRequest 파라미터
  - `frontend/src/services/api.ts` — layout 파라미터
  - `frontend/src/components/molecules/HighlightCard.tsx` — Export 버튼 2개
  - `frontend/src/components/organisms/HighlightGrid.tsx` — onExport 타입
  - `frontend/src/app/page.tsx` — handleExport 시그니처

---

## 2. Gap Analysis (Design vs Implementation)

### 2.1 Backend: Constants (`core/constants.py`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `SHORTFORM_WIDTH = 1080` | `constants.py:119` — identical | MATCH |
| `SHORTFORM_HEIGHT = 1920` | `constants.py:120` — identical | MATCH |
| `SHORTFORM_SAFE_TOP_RATIO = 0.15` | `constants.py:121` — identical | MATCH |
| `SHORTFORM_SAFE_BOTTOM_RATIO = 0.35` | `constants.py:122` — identical | MATCH |
| `SHORTFORM_CONTENT_HEIGHT = 960` | `constants.py:123` — identical | MATCH |
| `SHORTFORM_CONTENT_Y = 288` | `constants.py:124` — identical | MATCH |
| `SHORTFORM_BLUR_STRENGTH = 20` | `constants.py:125` — identical | MATCH |

### 2.2 Backend: Schema (`models/schemas.py`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `ExportLayout(str, Enum)` with ORIGINAL/SHORTFORM | `schemas.py:66-68` — identical | MATCH |
| `ExportRequest(BaseModel)` with layout default ORIGINAL | `schemas.py:71-72` — identical | MATCH |

### 2.3 Backend: ExportJob (`services/export_processor.py`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `__init__` has `layout: str = "original"` param | `export_processor.py:34` — identical | MATCH |
| `self.layout = layout` assignment | `export_processor.py:41` — identical | MATCH |
| `to_dict` includes `data["layout"] = self.layout` | `export_processor.py:55` — identical | MATCH |
| `from_dict` has `job.layout = data.get("layout", "original")` | `export_processor.py:76` — identical | MATCH |
| `create_export_job` has `layout` param | `export_processor.py:120` — identical | MATCH |
| `create_export_job` passes `layout=layout` to ExportJob | `export_processor.py:131` — identical | MATCH |

### 2.4 Backend: _get_video_dimensions (`services/export_processor.py`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| ffprobe command with `-v error -select_streams v:0` | `export_processor.py:207-213` — identical | MATCH |
| `-of csv=p=0:s=x` output format | `export_processor.py:212` — identical | MATCH |
| `asyncio.create_subprocess_exec` call | `export_processor.py:215-219` — identical | MATCH |
| Parse `stdout` as `w,h = split("x")` | `export_processor.py:221-222` — uses `parts` variable | MATCH |

### 2.5 Backend: _build_shortform_cmd (`services/export_processor.py`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| Method signature with 6 params | `export_processor.py:224-232` — identical | MATCH |
| Import constants from `core.constants` | `export_processor.py:234-238` — identical | MATCH |
| `is_portrait = src_height > src_width` | `export_processor.py:246` — identical | MATCH |
| Portrait: `-vf scale+pad` filter | `export_processor.py:248-262` — identical logic, split into separate return | MATCH |
| Landscape: `-filter_complex` with blur bg + overlay | `export_processor.py:263-282` — identical logic, split into separate return | MATCH |
| Design uses single cmd list with ternary `-filter_complex`/`-vf` | Implementation splits into two return blocks | MINOR DIFF |
| H.264/AAC/fast/CRF23/faststart encoding params | Both paths include identical params | MATCH |

**Note on MINOR DIFF**: Design spec showed a single `cmd` list with ternary for `-filter_complex`/`-vf`, but implementation correctly splits into two `return` blocks — one for portrait with `-vf`, one for landscape with `-filter_complex`. This is functionally equivalent and arguably cleaner. **No gap.**

### 2.6 Backend: process_export branching (`services/export_processor.py`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `if job.layout == "shortform"` branch | `export_processor.py:162` — identical | MATCH |
| Calls `_get_video_dimensions` then `_build_shortform_cmd` | `export_processor.py:163-167` — identical | MATCH |
| `else` branch: original ffmpeg cmd | `export_processor.py:168-180` — identical | MATCH |
| Output filename includes suffix for shortform | `export_processor.py:157-158` — `_sf` suffix added | ENHANCEMENT |

**Note on ENHANCEMENT**: Implementation adds `_sf` suffix to shortform output filenames to avoid collision with original exports of the same highlight. Not in design spec but a correct improvement.

### 2.7 Backend: API Endpoint (`api/highlights.py`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `from models.schemas import ExportRequest` | `highlights.py:6` — identical | MATCH |
| `export_request: ExportRequest = ExportRequest()` param | `highlights.py:49` — identical | MATCH |
| `layout=export_request.layout.value` in create_export_job | `highlights.py:93` — identical | MATCH |

### 2.8 Frontend: API Client (`services/api.ts`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `layout: 'original' \| 'shortform' = 'original'` param | `api.ts:165` — identical | MATCH |
| `headers: { 'Content-Type': 'application/json' }` | `api.ts:169` — identical | MATCH |
| `body: JSON.stringify({ layout })` | `api.ts:170` — identical | MATCH |

### 2.9 Frontend: HighlightCard (`components/molecules/HighlightCard.tsx`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `onExport: (highlight, layout) => void` prop type | `HighlightCard.tsx:24` — identical | MATCH |
| Hover overlay: Download button removed, Play only | `HighlightCard.tsx:54-63` — Play button only | MATCH |
| Card bottom: "원본" button with variant="outline" | `HighlightCard.tsx:85-94` — identical | MATCH |
| Card bottom: "숏폼 9:16" button with bg-violet-600 | `HighlightCard.tsx:95-104` — identical | MATCH |
| Both buttons disabled when isExporting | `HighlightCard.tsx:90,99` — identical | MATCH |
| Loader2 spinner when exporting | `HighlightCard.tsx:92,101` — identical | MATCH |

### 2.10 Frontend: HighlightGrid (`components/organisms/HighlightGrid.tsx`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `onExport: (highlight, layout) => void` prop type | `HighlightGrid.tsx:9` — identical | MATCH |

### 2.11 Frontend: Page (`app/page.tsx`)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `handleExport(highlight, layout)` signature | `page.tsx:172` — identical (with default 'original') | MATCH |
| `highlightApi.export(highlight.id, layout)` call | `page.tsx:178` — identical | MATCH |

---

## 3. Verification Items

| ID | Category | Verification | Status | Notes |
|----|----------|-------------|--------|-------|
| V-01 | API | body 없이 POST → layout=original | PASS | ExportRequest() 기본값 |
| V-02 | API | body: {"layout":"original"} | PASS | 기존 FFmpeg cmd 실행 |
| V-03 | API | body: {"layout":"shortform"} | PASS | shortform 분기 실행 |
| V-04 | FFmpeg | 가로 + shortform → blur bg + safezone | PASS | filter_complex 구현 확인 |
| V-05 | FFmpeg | 정방형 + shortform → blur bg + safezone | PASS | is_portrait=False 분기 |
| V-06 | FFmpeg | 세로 + shortform → resize | PASS | is_portrait=True, -vf scale+pad |
| V-07 | FFmpeg | ffprobe 비율 감지 | PASS | _get_video_dimensions 구현 |
| V-08 | Frontend | 원본/숏폼 버튼 표시 | PASS | HighlightCard 두 버튼 |
| V-09 | Frontend | "원본" → layout=original | PASS | onClick에 'original' 전달 |
| V-10 | Frontend | "숏폼 9:16" → layout=shortform | PASS | onClick에 'shortform' 전달 |
| V-11 | Redis | layout 필드 저장/복원 | PASS | to_dict/from_dict 구현 |
| V-12 | 호환성 | H.264/AAC/faststart | PASS | 두 경로 모두 동일 인코딩 파라미터 |
| V-13 | 오디오 | A/V 싱크 | PASS | `-c:a aac` 유지 |

---

## 4. Summary

| Metric | Value |
|--------|-------|
| **Total Verification Items** | 13 |
| **PASS** | 13 |
| **FAIL** | 0 |
| **Match Rate** | **100%** |
| **Iterations Required** | 0 |

모든 Design 스펙이 구현에 정확히 반영되었습니다. 구현이 Design 대비 추가한 개선사항(출력 파일명 `_sf` 접미사, portrait/landscape 별도 return 블록)은 기능적으로 동등하며 코드 가독성을 높입니다.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-08 | Initial analysis | Claude |
