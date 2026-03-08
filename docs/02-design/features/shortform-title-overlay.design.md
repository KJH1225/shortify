# shortform-title-overlay Design Document

> **Summary**: 숏폼(9:16) 내보내기 시 FFmpeg drawtext 필터로 하이라이트 제목을 영상 상단에 오버레이
>
> **Project**: Shortify
> **Version**: 0.1.0
> **Date**: 2026-03-09
> **Status**: Draft
> **Planning Doc**: [shortform-title-overlay.plan.md](../../01-plan/features/shortform-title-overlay.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- 숏폼 레이아웃 내보내기 시 하이라이트 title을 영상 상단 safe zone에 자동 오버레이
- FFmpeg `drawtext` 필터를 기존 shortform filter_complex 체인에 추가
- 원본(original) 레이아웃에는 영향 없음
- title이 없거나 빈 문자열인 경우 텍스트 오버레이 생략

### 1.2 Design Principles

- 기존 `_build_shortform_cmd()`, `_build_shortform_concat_cmd()` 확장
- 새 메서드/클래스 생성 최소화 — drawtext 필터 문자열 생성 헬퍼 1개만 추가
- 한글 특수문자 이스케이프 처리로 FFmpeg 호환성 확보

---

## 2. Architecture

### 2.1 변경 대상 파일

| Layer | File | Change |
|-------|------|--------|
| Backend Constants | `core/constants.py` | 제목 오버레이 상수 추가 (폰트, 크기, 위치, 색상) |
| Backend Service | `services/export_processor.py` | ExportJob에 title 필드 + `_build_drawtext_filter()` 메서드 + 기존 shortform 메서드에 drawtext 통합 |
| Backend API | `api/highlights.py` | highlight.title을 create_export_job()에 전달 |

### 2.2 변경하지 않는 파일

| File | Reason |
|------|--------|
| `models/schemas.py` | title은 백엔드에서 DB 조회로 자동 전달 — ExportRequest 변경 불필요 |
| Frontend 전체 | 프론트에서 title을 보내지 않아도 됨 — API 요청 변경 없음 |

### 2.3 Data Flow

```
User clicks "숏폼 9:16" Export
  → POST /api/highlights/{id}/export  body: { layout: "shortform" }
    → api/highlights.py: DB에서 highlight.title 조회
      → create_export_job(title=highlight.title, ...)
        → ExportJob(title="핵심 개념 설명", layout="shortform", ...)
          → process_export(job)
            → _build_shortform_cmd(title=job.title, ...)
              → filter_complex에 drawtext 필터 추가
                → FFmpeg 실행 → 제목 오버레이된 1080x1920 영상 출력
```

---

## 3. Backend Design

### 3.1 Constants (`core/constants.py`)

기존 Shortform 상수 블록 하단에 추가:

```python
# Shortform title overlay constants
SHORTFORM_TITLE_FONTSIZE = 52
SHORTFORM_TITLE_Y = 130              # safe zone 내부 (상단 288px 영역 중앙 부근)
SHORTFORM_TITLE_FONTCOLOR = "white"
SHORTFORM_TITLE_BORDERW = 3          # 텍스트 외곽선 두께
SHORTFORM_TITLE_SHADOWCOLOR = "black@0.5"
SHORTFORM_TITLE_SHADOWX = 2
SHORTFORM_TITLE_SHADOWY = 2
SHORTFORM_TITLE_FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
```

**폰트 전략**:
- macOS: `/System/Library/Fonts/AppleSDGothicNeo.ttc` (시스템 내장, 한글 지원)
- Linux/Docker: Dockerfile에 `fonts-nanum` 또는 `noto-cjk` 패키지 설치 후 경로 변경
- `fontfile` 경로가 존재하지 않으면 drawtext 생략 (graceful fallback)

### 3.2 ExportJob 변경 (`services/export_processor.py`)

#### 3.2.1 `ExportJob.__init__` — title 필드 추가

```python
def __init__(
    self,
    export_id: str,
    highlight_id: int,
    video_path: str,
    start_time: float,
    end_time: float,
    layout: str = "original",
    clips: list[dict] | None = None,
    title: str = "",                  # NEW
):
    # ... existing fields ...
    self.title = title                # NEW
```

#### 3.2.2 `to_dict` / `from_dict` — title 직렬화

```python
# to_dict에 추가
data["title"] = self.title

# from_dict에 추가
job.title = data.get("title", "")
```

#### 3.2.3 `create_export_job` — title 파라미터 추가

```python
async def create_export_job(
    self,
    highlight_id: int,
    video_path: str,
    start_time: float,
    end_time: float,
    layout: str = "original",
    clips: list[dict] | None = None,
    title: str = "",                  # NEW
) -> ExportJob:
    export_id = f"export_{uuid.uuid4().hex[:8]}"
    job = ExportJob(
        export_id=export_id,
        highlight_id=highlight_id,
        video_path=video_path,
        start_time=start_time,
        end_time=end_time,
        layout=layout,
        clips=clips,
        title=title,                  # NEW
    )
    await self._save_job(job)
    return job
```

### 3.3 drawtext 필터 빌드 메서드 (NEW)

```python
def _build_drawtext_filter(self, title: str) -> str:
    """제목 텍스트 drawtext 필터 문자열 생성. title이 없거나 폰트 없으면 빈 문자열 반환."""
    if not title:
        return ""

    from core.constants import (
        SHORTFORM_TITLE_FONTSIZE, SHORTFORM_TITLE_Y,
        SHORTFORM_TITLE_FONTCOLOR, SHORTFORM_TITLE_BORDERW,
        SHORTFORM_TITLE_SHADOWCOLOR,
        SHORTFORM_TITLE_SHADOWX, SHORTFORM_TITLE_SHADOWY,
        SHORTFORM_TITLE_FONT,
    )

    # 폰트 파일 존재 확인
    if not os.path.exists(SHORTFORM_TITLE_FONT):
        return ""

    # FFmpeg drawtext 특수문자 이스케이프
    escaped = title.replace("\\", "\\\\").replace("'", "'\\\\\\''").replace(":", "\\:")

    return (
        f"drawtext=text='{escaped}'"
        f":fontfile='{SHORTFORM_TITLE_FONT}'"
        f":fontsize={SHORTFORM_TITLE_FONTSIZE}"
        f":fontcolor={SHORTFORM_TITLE_FONTCOLOR}"
        f":borderw={SHORTFORM_TITLE_BORDERW}"
        f":bordercolor=black"
        f":shadowcolor={SHORTFORM_TITLE_SHADOWCOLOR}"
        f":shadowx={SHORTFORM_TITLE_SHADOWX}"
        f":shadowy={SHORTFORM_TITLE_SHADOWY}"
        f":x=(w-text_w)/2"
        f":y={SHORTFORM_TITLE_Y}"
    )
```

**특수문자 이스케이프 규칙**:
| Character | Escape | Reason |
|-----------|--------|--------|
| `\` | `\\\\` | FFmpeg 이스케이프 |
| `'` | `'\\\\\\''` | shell + FFmpeg 이중 이스케이프 |
| `:` | `\\:` | FFmpeg 옵션 구분자와 충돌 |

### 3.4 기존 shortform 메서드 수정

#### 3.4.1 `_build_shortform_cmd` — 단일 클립

drawtext를 filter_complex 체인 마지막에 추가. `setsar=1` 뒤에 삽입.

**Portrait 케이스 (현재 `-vf` 사용)**:
```python
# Before (현재)
vf = f"scale=...pad=...,setsar=1"

# After (title 있을 때)
drawtext = self._build_drawtext_filter(title)
if drawtext:
    vf = f"scale=...pad=...,setsar=1,{drawtext}"
```

**Landscape 케이스 (현재 `-filter_complex` 사용)**:
```python
# Before (현재)
filter_complex = "...[bg];...[fg];[bg][fg]overlay=...,setsar=1"

# After (title 있을 때)
drawtext = self._build_drawtext_filter(title)
suffix = f",{drawtext}" if drawtext else ""
filter_complex = f"...[bg];...[fg];[bg][fg]overlay=...,setsar=1{suffix}"
```

#### 3.4.2 `_build_shortform_concat_cmd` — 멀티 클립

마찬가지로 최종 `[outv]` 라벨 생성 직전에 drawtext 삽입.

**Portrait 케이스**:
```python
# Before
filter_parts.append(f"[cv]scale=...pad=...,setsar=1[outv]")

# After
drawtext = self._build_drawtext_filter(title)
dt = f",{drawtext}" if drawtext else ""
filter_parts.append(f"[cv]scale=...pad=...,setsar=1{dt}[outv]")
```

**Landscape 케이스**:
```python
# Before (마지막 filter_part)
f"[bg][fg]overlay=...,setsar=1[outv]"

# After
drawtext = self._build_drawtext_filter(title)
dt = f",{drawtext}" if drawtext else ""
f"[bg][fg]overlay=...,setsar=1{dt}[outv]"
```

### 3.5 메서드 시그니처 변경

두 shortform 메서드에 `title` 파라미터 추가:

```python
def _build_shortform_cmd(
    self,
    input_path: str,
    output_path: str,
    start_time: float,
    duration: float,
    src_width: int,
    src_height: int,
    title: str = "",                  # NEW
) -> list[str]:

def _build_shortform_concat_cmd(
    self,
    input_path: str,
    output_path: str,
    clips: list[dict],
    src_width: int,
    src_height: int,
    title: str = "",                  # NEW
) -> list[str]:
```

### 3.6 `process_export` 호출부 수정

```python
# 단일 클립 shortform
cmd = self._build_shortform_cmd(
    job.video_path, str(output_path),
    job.start_time, duration, src_w, src_h,
    title=job.title,                  # NEW
)

# 멀티 클립 shortform
cmd = self._build_shortform_concat_cmd(
    job.video_path, str(output_path), job.clips,
    src_w, src_h,
    title=job.title,                  # NEW
)
```

### 3.7 API Endpoint (`api/highlights.py`)

`export_highlight` 함수에서 title 전달:

```python
job = await export_processor.create_export_job(
    highlight_id=highlight_id,
    video_path=video_path or "",
    start_time=highlight.start_time,
    end_time=highlight.end_time,
    layout=export_request.layout.value,
    clips=highlight.clips,
    title=highlight.title or "",      # NEW
)
```

---

## 4. Visual Specification

### 4.1 레이아웃 다이어그램

```
┌──────────────────────────┐  ← 0px
│      Safe Zone Top       │
│  ┌──────────────────────┐│
│  │   "핵심 개념 설명"    ││  ← y=130px (제목 텍스트)
│  │   white, bold, 52px   ││
│  │   center aligned      ││
│  └──────────────────────┘│
│                          │  ← 288px (SHORTFORM_CONTENT_Y)
│  ┌──────────────────────┐│
│  │                      ││
│  │   Video Content      ││  ← 960px height
│  │   (blur background)  ││
│  │                      ││
│  └──────────────────────┘│  ← 1248px
│                          │
│   Safe Zone Bottom       │
│   (자막/UI 영역)         │
│                          │
└──────────────────────────┘  ← 1920px

Width: 1080px
```

### 4.2 텍스트 스타일

| Property | Value | Note |
|----------|-------|------|
| Font | Apple SD Gothic Neo | macOS 시스템 폰트, Bold weight |
| Size | 52px | 1080px 폭에서 가독성 확보 |
| Color | white (#FFFFFF) | 어두운 배경(blur)에서 높은 대비 |
| Border | 3px black | 텍스트 외곽선으로 추가 가독성 |
| Shadow | black@0.5, offset 2,2 | 부드러운 그림자 효과 |
| Alignment | 수평 중앙 | `x=(w-text_w)/2` |
| Y Position | 130px | 상단 safe zone(0~288px) 중앙 부근 |

---

## 5. Edge Cases

| Case | Behavior |
|------|----------|
| title이 빈 문자열 또는 None | drawtext 필터 생략, 기존 동작과 동일 |
| title에 `'`, `:`, `\` 포함 | FFmpeg 이스케이프 처리 |
| 폰트 파일 미존재 (Linux 등) | drawtext 생략, 텍스트 없이 숏폼 출력 |
| layout이 "original"인 경우 | title 무시, 기존 동작 |
| 매우 긴 title (20자 이상) | 하이라이트 title은 AI가 20자 이내로 생성하므로 문제 없음. 만약 초과 시 화면 밖으로 나갈 수 있으나 현실적으로 발생 안 함 |

---

## 6. Verification Items

| ID | Category | Verification | Expected Result |
|----|----------|-------------|-----------------|
| V-01 | drawtext | 숏폼 단일 클립 + title 있음 | 영상 상단에 흰색 제목 텍스트 표시 |
| V-02 | drawtext | 숏폼 멀티 클립 + title 있음 | 영상 상단에 흰색 제목 텍스트 표시 |
| V-03 | drawtext | 숏폼 + title 없음 (빈 문자열) | 텍스트 없이 기존 숏폼과 동일 |
| V-04 | drawtext | title에 특수문자 포함 ("'작은따옴표'") | 이스케이프 처리되어 정상 표시 |
| V-05 | drawtext | title에 콜론 포함 ("시간:분석") | 이스케이프 처리되어 정상 표시 |
| V-06 | fallback | 폰트 파일 미존재 | drawtext 생략, 에러 없이 숏폼 출력 |
| V-07 | layout | original 레이아웃 + title | title 무시, 기존 원본 출력 |
| V-08 | Redis | ExportJob title 직렬화/역직렬화 | to_dict/from_dict에서 title 유지 |
| V-09 | API | export 엔드포인트에서 title 전달 | highlight.title이 ExportJob에 저장됨 |
| V-10 | Visual | 텍스트 가독성 | 블러 배경 위에서 흰색 텍스트 + 검정 테두리 선명하게 보임 |

---

## 7. Implementation Order

1. [ ] `core/constants.py` — 제목 오버레이 상수 추가
2. [ ] `services/export_processor.py` — ExportJob title 필드 + `_build_drawtext_filter()` + shortform 메서드 수정
3. [ ] `api/highlights.py` — title 전달

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial draft | Claude |
