# shortform-layout Design Document

> **Summary**: Export 시 원본/숏폼(9:16) 레이아웃 선택 + FFmpeg 필터 체인 세이프존 적용
>
> **Project**: Shortify
> **Version**: 0.2.0
> **Date**: 2026-03-08
> **Status**: Draft
> **Planning Doc**: [shortform-layout.plan.md](../../01-plan/features/shortform-layout.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- 기존 Export 파이프라인에 `layout` 파라미터를 추가하여 원본/숏폼 선택 지원
- 숏폼 모드에서 FFmpeg 필터 체인으로 9:16 캔버스 + 세이프존 + 블러 배경 자동 적용
- 기존 API/프론트엔드와 하위 호환 유지 (`layout` 미지정 시 `original`)

### 1.2 Design Principles

- 기존 `ExportProcessor` 클래스 확장 (새 클래스 생성 불필요)
- FFmpeg 커맨드 빌드 로직만 분기 — 나머지 파이프라인(Job 생성, Redis 저장, 상태 관리) 재사용
- 상수값(캔버스 크기, 세이프존 비율)은 `constants.py`에서 관리

---

## 2. Architecture

### 2.1 변경 대상 파일

| Layer | File | Change |
|-------|------|--------|
| Backend API | `api/highlights.py` | Export 엔드포인트에 `layout` body 파라미터 추가 |
| Backend Schema | `models/schemas.py` | `ExportRequest` Pydantic 모델 추가 |
| Backend Service | `services/export_processor.py` | `ExportJob`에 `layout` 필드, `_build_shortform_cmd()` 메서드 추가 |
| Backend Constants | `core/constants.py` | 숏폼 레이아웃 상수 추가 |
| Frontend API | `services/api.ts` | `highlightApi.export()`에 `layout` 파라미터 추가 |
| Frontend Component | `components/molecules/HighlightCard.tsx` | Export 레이아웃 선택 토글 UI 추가 |
| Frontend Page | `app/page.tsx` | `handleExport`에 `layout` 전달 |

### 2.2 Data Flow

```
User clicks Export with layout selection
  → HighlightCard: onExport(highlight, layout)
    → page.tsx: handleExport(highlight, layout)
      → highlightApi.export(highlightId, layout)
        → POST /api/highlights/{id}/export  body: { layout: "shortform" }
          → export_highlight(): create job with layout
            → BackgroundTask: process_export(job)
              → layout == "original" ? _build_original_cmd()
              →                        _build_shortform_cmd()
                → ffprobe → ffmpeg filter_complex → 1080x1920 output
```

---

## 3. Backend Design

### 3.1 Constants (`core/constants.py`)

파일 하단에 추가:

```python
# Shortform layout constants
SHORTFORM_WIDTH = 1080
SHORTFORM_HEIGHT = 1920
SHORTFORM_SAFE_TOP_RATIO = 0.15      # 상단 15% = 288px
SHORTFORM_SAFE_BOTTOM_RATIO = 0.35   # 하단 35% = 672px
SHORTFORM_CONTENT_HEIGHT = 960       # 1920 * (1 - 0.15 - 0.35)
SHORTFORM_CONTENT_Y = 288            # 1920 * 0.15
SHORTFORM_BLUR_STRENGTH = 20         # boxblur 강도
```

### 3.2 Schema (`models/schemas.py`)

Pydantic 모델 추가:

```python
from enum import Enum

class ExportLayout(str, Enum):
    ORIGINAL = "original"
    SHORTFORM = "shortform"

class ExportRequest(BaseModel):
    layout: ExportLayout = ExportLayout.ORIGINAL
```

### 3.3 ExportJob 변경 (`services/export_processor.py`)

#### 3.3.1 `ExportJob.__init__` — `layout` 필드 추가

```python
def __init__(
    self,
    export_id: str,
    highlight_id: int,
    video_path: str,
    start_time: float,
    end_time: float,
    layout: str = "original",    # NEW
):
    # ... existing fields ...
    self.layout = layout          # NEW
```

#### 3.3.2 `ExportJob.to_dict` / `from_dict` — `layout` 직렬화

```python
# to_dict에 추가
data["layout"] = self.layout

# from_dict에 추가
job.layout = data.get("layout", "original")
```

#### 3.3.3 `ExportProcessor.create_export_job` — `layout` 파라미터

```python
async def create_export_job(
    self,
    highlight_id: int,
    video_path: str,
    start_time: float,
    end_time: float,
    layout: str = "original",    # NEW
) -> ExportJob:
    export_id = f"export_{uuid.uuid4().hex[:8]}"
    job = ExportJob(
        export_id=export_id,
        highlight_id=highlight_id,
        video_path=video_path,
        start_time=start_time,
        end_time=end_time,
        layout=layout,            # NEW
    )
    await self._save_job(job)
    return job
```

#### 3.3.4 `ExportProcessor._get_video_dimensions` — ffprobe 비율 감지 (NEW)

```python
async def _get_video_dimensions(self, video_path: str) -> tuple[int, int]:
    """ffprobe로 영상 width/height 조회"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x",
        video_path,
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    # output format: "1920x1080"
    w, h = stdout.decode().strip().split("x")
    return int(w), int(h)
```

#### 3.3.5 `ExportProcessor._build_shortform_cmd` — FFmpeg 필터 체인 (NEW)

```python
def _build_shortform_cmd(
    self,
    input_path: str,
    output_path: str,
    start_time: float,
    duration: float,
    src_width: int,
    src_height: int,
) -> list[str]:
    """9:16 숏폼 레이아웃 FFmpeg 커맨드 빌드"""
    from core.constants import (
        SHORTFORM_WIDTH, SHORTFORM_HEIGHT,
        SHORTFORM_CONTENT_HEIGHT, SHORTFORM_CONTENT_Y,
        SHORTFORM_BLUR_STRENGTH,
    )

    W = SHORTFORM_WIDTH       # 1080
    H = SHORTFORM_HEIGHT      # 1920
    CY = SHORTFORM_CONTENT_Y  # 288
    CH = SHORTFORM_CONTENT_HEIGHT  # 960
    BLUR = SHORTFORM_BLUR_STRENGTH  # 20

    is_portrait = src_height > src_width

    if is_portrait:
        # Portrait: 단순 리사이즈
        filter_complex = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2"
    else:
        # Landscape/Square: 블러 배경 + 세이프존 내 콘텐츠
        # [0:v] → 배경(블러) + 콘텐츠(fit) overlay
        # 콘텐츠를 1080xCH 안에 fit
        filter_complex = (
            f"[0:v]scale={W}:{H},boxblur={BLUR}:{BLUR}[bg];"
            f"[0:v]scale='if(gt(iw/ih,{W}/{CH}),{W},-2)':'if(gt(iw/ih,{W}/{CH}),-2,{CH})'[fg];"
            f"[bg][fg]overlay=(W-w)/2:{CY}+(({CH}-h)/2)"
        )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", input_path,
        "-t", str(duration),
        "-filter_complex" if not is_portrait else "-vf",
        filter_complex,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-preset", "fast",
        "-crf", "23",
        "-movflags", "+faststart",
        str(output_path),
    ]
    return cmd
```

#### 3.3.6 `ExportProcessor.process_export` — 분기 로직 (MODIFY)

`process_export`의 기존 FFmpeg 커맨드 빌드 부분(`export_processor.py:154-167`)을 분기:

```python
async def process_export(self, job: ExportJob) -> ExportJob:
    # ... existing validation (lines 132-147) ...

    duration = job.end_time - job.start_time
    output_filename = f"{job.highlight_id}_{int(job.start_time)}_{int(job.end_time)}.mp4"
    output_path = self.output_dir / output_filename

    try:
        if job.layout == "shortform":
            src_w, src_h = await self._get_video_dimensions(job.video_path)
            cmd = self._build_shortform_cmd(
                job.video_path, str(output_path),
                job.start_time, duration, src_w, src_h,
            )
        else:
            # Original: 기존 커맨드 그대로
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(job.start_time),
                "-i", job.video_path,
                "-t", str(duration),
                "-c:v", "libx264", "-c:a", "aac",
                "-preset", "fast", "-crf", "23",
                "-movflags", "+faststart",
                str(output_path),
            ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # ... existing result handling (lines 175-183) ...
```

### 3.4 API Endpoint (`api/highlights.py`)

#### `export_highlight` 엔드포인트 변경

```python
from models.schemas import ExportRequest

@router.post("/{highlight_id}/export")
async def export_highlight(
    highlight_id: int,
    background_tasks: BackgroundTasks,
    export_request: ExportRequest = ExportRequest(),  # NEW: body 파라미터
    db: AsyncSession = Depends(get_db),
):
    # ... existing highlight/video lookup (lines 51-84) ...

    # Create export job with layout
    job = await export_processor.create_export_job(
        highlight_id=highlight_id,
        video_path=video_path or "",
        start_time=highlight.start_time,
        end_time=highlight.end_time,
        layout=export_request.layout.value,   # NEW
    )

    # ... existing estimated_time, background_tasks (lines 94-113) ...
```

**하위 호환**: `ExportRequest`의 `layout` 기본값이 `"original"`이므로 body 없이 POST해도 기존 동작과 동일하다.

---

## 4. Frontend Design

### 4.1 Type 변경 없음

`ExportLayout` 타입은 `api.ts`에서 문자열 리터럴로 처리 — 별도 types/index.ts 변경 불필요.

### 4.2 API Client (`services/api.ts`)

#### `highlightApi.export` 변경

```typescript
export const highlightApi = {
  // ...

  export: async (
    highlightId: number,
    layout: 'original' | 'shortform' = 'original',  // NEW
  ): Promise<ApiResponse<ExportResponse>> => {
    const response = await fetch(`${API_URL}/api/highlights/${highlightId}/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },   // NEW
      body: JSON.stringify({ layout }),                    // NEW
    });
    return handleResponse(response);
  },

  // ...
};
```

### 4.3 HighlightCard 변경 (`components/molecules/HighlightCard.tsx`)

#### Props 인터페이스 변경

```typescript
interface HighlightCardProps {
  highlight: Highlight;
  onPlay: (highlight: Highlight) => void;
  onExport: (highlight: Highlight, layout: 'original' | 'shortform') => void;  // CHANGED
  isExporting?: boolean;
}
```

#### Export 버튼 영역 변경 (카드 하단 `p-4` 영역)

기존 hover overlay의 Download 버튼 대신, 카드 하단에 **두 개의 Export 버튼**을 배치:

```
┌────────────────────────────────┐
│  [Thumbnail / Play overlay]    │
│                                │
│  duration badge                │
├────────────────────────────────┤
│  Title                         │
│  Description                   │
│  Time range          Score     │
│                                │
│  [원본 Export]  [숏폼 Export]   │  ← NEW: 두 버튼
└────────────────────────────────┘
```

```tsx
{/* Export buttons */}
<div className="flex gap-2 pt-2">
  <Button
    size="sm"
    variant="outline"
    className="flex-1 text-xs"
    onClick={() => onExport(highlight, 'original')}
    disabled={isExporting}
  >
    {isExporting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Download className="h-3 w-3 mr-1" />}
    원본
  </Button>
  <Button
    size="sm"
    variant="default"
    className="flex-1 text-xs bg-violet-600 hover:bg-violet-700"
    onClick={() => onExport(highlight, 'shortform')}
    disabled={isExporting}
  >
    {isExporting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Download className="h-3 w-3 mr-1" />}
    숏폼 9:16
  </Button>
</div>
```

hover overlay의 Download 버튼은 제거하고 Play 버튼만 유지.

### 4.4 Page 변경 (`app/page.tsx`)

#### `handleExport` 시그니처 변경

```typescript
const handleExport = async (highlight: Highlight, layout: 'original' | 'shortform') => {
  // ... existing guard ...
  try {
    const response = await highlightApi.export(highlight.id, layout);  // layout 전달
    // ... existing polling logic ...
```

#### `HighlightGrid` → `HighlightCard`로 전달

`onExport` prop이 `(highlight, layout)` 시그니처를 받으므로 `HighlightGrid`도 타입 맞춤:

```typescript
<HighlightGrid
  highlights={highlights}
  onPlay={handlePlay}
  onExport={handleExport}   // 이미 (highlight, layout) 시그니처
  exportingHighlightId={exportingHighlightId}
/>
```

### 4.5 HighlightGrid 변경 (`components/organisms/HighlightGrid.tsx`)

`onExport` prop 타입을 HighlightCard와 일치시킴:

```typescript
interface HighlightGridProps {
  highlights: Highlight[];
  onPlay: (highlight: Highlight) => void;
  onExport: (highlight: Highlight, layout: 'original' | 'shortform') => void;  // CHANGED
  exportingHighlightId: number | null;
}
```

---

## 5. Verification Items

| ID | Category | Verification | Expected Result |
|----|----------|-------------|-----------------|
| V-01 | API | `POST /api/highlights/{id}/export` body 없이 호출 | layout=original로 동작 (기존 동작 유지) |
| V-02 | API | `POST /api/highlights/{id}/export` body: `{"layout":"original"}` | 원본 비율 클리핑 |
| V-03 | API | `POST /api/highlights/{id}/export` body: `{"layout":"shortform"}` | 1080x1920 출력 |
| V-04 | FFmpeg | 가로(16:9) 영상 + shortform | 세이프존 내 배치, 블러 배경, 1080x1920 |
| V-05 | FFmpeg | 정방형(1:1) 영상 + shortform | 세이프존 내 배치, 블러 배경, 1080x1920 |
| V-06 | FFmpeg | 세로(9:16) 영상 + shortform | 리사이즈, 1080x1920 |
| V-07 | FFmpeg | ffprobe 비율 감지 | width/height 정확히 반환 |
| V-08 | Frontend | HighlightCard에 원본/숏폼 버튼 표시 | 두 버튼 모두 렌더링 |
| V-09 | Frontend | "원본" 버튼 클릭 | layout=original로 API 호출 |
| V-10 | Frontend | "숏폼 9:16" 버튼 클릭 | layout=shortform으로 API 호출 |
| V-11 | Redis | ExportJob에 layout 필드 저장/복원 | to_dict/from_dict에서 layout 유지 |
| V-12 | 호환성 | 출력 MP4가 H.264/AAC, faststart | 숏폼 플랫폼 호환 |
| V-13 | 오디오 | 숏폼 모드 출력에서 오디오 싱크 | A/V 싱크 유지 |

---

## 6. Implementation Order

1. [ ] `core/constants.py` — 숏폼 상수 추가 (SHORTFORM_WIDTH 등)
2. [ ] `models/schemas.py` — `ExportLayout`, `ExportRequest` 추가
3. [ ] `services/export_processor.py` — ExportJob에 layout, _get_video_dimensions, _build_shortform_cmd, process_export 분기
4. [ ] `api/highlights.py` — export_highlight에 ExportRequest 파라미터 추가
5. [ ] `frontend/src/services/api.ts` — highlightApi.export에 layout 파라미터
6. [ ] `frontend/src/components/molecules/HighlightCard.tsx` — Export 버튼 2개 (원본/숏폼)
7. [ ] `frontend/src/components/organisms/HighlightGrid.tsx` — onExport 타입 변경
8. [ ] `frontend/src/app/page.tsx` — handleExport 시그니처 변경

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-08 | Initial draft | Claude |
