# multimodal-highlight Design Document

> **Summary**: 멀티모달 분석(키프레임+오디오+장면전환) + 서브클립 자동 편집
>
> **Project**: Shortify
> **Version**: 0.3.0
> **Date**: 2026-03-08
> **Status**: Draft
> **Planning Doc**: [multimodal-highlight.plan.md](../../01-plan/features/multimodal-highlight.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- FFmpeg로 키프레임/오디오 에너지/장면 전환을 추출하여 GPT-4o 멀티모달 API에 전달
- 하이라이트를 서브클립 배열(`clips`)로 반환받아 불필요한 구간 제거 + 편집된 Export
- 기존 단일 구간 하이라이트와 하위 호환 유지

---

## 2. New Files (3개)

### 2.1 `services/keyframe_extractor.py`

```python
class KeyframeExtractor:
    async def extract(self, video_path: str, output_dir: str,
                      interval: int = 10, max_count: int = 30,
                      width: int = 512) -> list[KeyframeInfo]:
        """
        FFmpeg로 N초 간격 키프레임 JPEG 추출 + base64 인코딩

        FFmpeg command:
          ffmpeg -i {video} -vf "fps=1/{interval},scale={width}:-1"
                 -q:v 5 {output_dir}/frame_%04d.jpg

        Returns: [{timestamp: float, base64: str}, ...]
        """
```

- `interval`: 프레임 추출 간격 (기본 10초)
- `max_count`: 최대 프레임 수 (기본 30, 초과 시 interval 자동 조정)
- `width`: 리사이즈 폭 (기본 512px, 비용 최적화)
- base64 인코딩하여 GPT API에 직접 전달 가능하게 반환
- 임시 JPEG 파일은 처리 후 삭제

### 2.2 `services/audio_analyzer.py`

```python
@dataclass
class AudioHotspot:
    timestamp: float    # 초
    rms_level: float    # dB
    description: str    # "volume_spike" | "silence_to_voice"

class AudioAnalyzer:
    async def analyze(self, audio_path: str,
                      top_n: int = 10) -> list[AudioHotspot]:
        """
        FFmpeg astats로 1초 단위 RMS 에너지 추출 후 핫스팟 식별

        FFmpeg command:
          ffmpeg -i {audio} -af astats=metadata=1:reset=1,
                 ametadata=print:key=lavfi.astats.Overall.RMS_level
                 -f null -

        Returns: 에너지 상위 N개 핫스팟 (볼륨 급상승, 무음→소리 전환 등)
        """
```

- FFmpeg stderr 출력에서 `lavfi.astats.Overall.RMS_level` 파싱
- 1초 단위 RMS 값 배열 생성
- 핫스팟 식별 전략:
  - 볼륨 급상승: 이전 5초 평균 대비 +6dB 이상
  - 무음→소리 전환: -50dB 이하 → -30dB 이상

### 2.3 `services/scene_detector.py`

```python
class SceneDetector:
    async def detect(self, video_path: str,
                     threshold: float = 0.3) -> list[float]:
        """
        FFmpeg scene detection으로 장면 전환 타임스탬프 추출

        FFmpeg command:
          ffmpeg -i {video} -vf "select='gt(scene,{threshold})',showinfo"
                 -f null -

        Returns: [12.5, 45.2, 78.0, ...] (초 단위 장면 전환 시점)
        """
```

- FFmpeg stderr에서 `pts_time:` 파싱
- `threshold`: 장면 변화 감도 (0.0~1.0, 기본 0.3)

---

## 3. Modified Files

### 3.1 `core/config.py` — 설정 추가

```python
# Multimodal analysis
openai_chat_model: str = "gpt-4o"          # gpt-4o-mini → gpt-4o
keyframe_interval: int = 10                 # 키프레임 간격 (초)
keyframe_max_count: int = 30                # 최대 키프레임 수
keyframe_width: int = 512                   # 리사이즈 폭 (px)
scene_threshold: float = 0.3               # 장면 전환 감도
audio_hotspot_count: int = 10              # 오디오 핫스팟 최대 수
```

### 3.2 `core/constants.py` — 멀티모달 프롬프트

기존 `HIGHLIGHT_SYSTEM_PROMPT`와 `HIGHLIGHT_USER_PROMPT`는 유지하고 (fallback용), 새 멀티모달 프롬프트 추가:

```python
MULTIMODAL_SYSTEM_PROMPT = """You are a professional video highlight extraction and editing expert.
You can see video frames, read transcripts, and analyze audio patterns.

Your task: Extract the most engaging highlights as EDITED CLIPS.
Each highlight can consist of MULTIPLE non-contiguous sub-clips
that are stitched together to form one cohesive short-form video.

Selection criteria:
- Visually impactful moments (expressions, actions, visual changes)
- Key information delivery with matching visuals
- Audio energy peaks (applause, laughter, music changes)
- Scene transitions that mark topic shifts
- Emotionally impactful moments

Editing rules:
- Remove filler, pauses, repetition, and off-topic segments
- Combine scattered relevant moments into one highlight
- Each clip within a highlight must be at least 3 seconds
- Total highlight duration: 15-60 seconds
- Clips must not overlap across highlights
- Score reflects importance (0.0-1.0)

Return JSON with clips array per highlight."""

MULTIMODAL_USER_PROMPT = """Video duration: {duration} seconds
Target highlight count: {target_count}

=== Transcript ===
{transcript}

=== Audio Hotspots ===
{audio_hotspots}

=== Scene Changes ===
{scene_changes}

Extract highlights as edited clips:
{{"highlights": [
  {{
    "title": "<highlight title>",
    "description": "<why this matters>",
    "score": <0.0-1.0>,
    "clips": [
      {{"start": <seconds>, "end": <seconds>}},
      {{"start": <seconds>, "end": <seconds>}}
    ]
  }}
]}}"""
```

### 3.3 `infrastructure/models.py` — clips 컬럼 추가

```python
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON

class Highlight(Base):
    # ... existing columns ...
    clips = Column(JSON, nullable=True)  # [{"start": 30, "end": 45}, ...]
```

- `clips`가 `None`이면 기존 방식 (start_time~end_time 단일 구간)
- `clips`가 있으면 서브클립 배열

### 3.4 `models/schemas.py` — Response에 clips 추가

```python
class ClipSegment(BaseModel):
    start: float
    end: float

class HighlightResponse(HighlightBase):
    id: int
    video_id: int
    clips: list[ClipSegment] | None = None
    created_at: datetime
```

### 3.5 `services/highlight_analyzer.py` — 멀티모달 분석 메서드

```python
class HighlightAnalyzer:
    # 기존 analyze() 유지 (fallback)

    async def analyze_multimodal(
        self,
        transcript: TranscriptionResult,
        keyframes: list[KeyframeInfo],
        audio_hotspots: list[AudioHotspot],
        scene_changes: list[float],
        duration: float,
    ) -> list[HighlightResult]:
        """멀티모달 + 서브클립 분석"""

        messages = [
            {"role": "system", "content": MULTIMODAL_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_multimodal_content(
                transcript, keyframes, audio_hotspots,
                scene_changes, duration,
            )},
        ]

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=4000,
        )
        # ... parse response with clips ...
```

`_build_multimodal_content`에서 `content` 배열 구성:
```python
content = [
    {"type": "text", "text": user_prompt_text},
]
for kf in keyframes:
    content.append({"type": "image_url", "image_url": {
        "url": f"data:image/jpeg;base64,{kf.base64}",
        "detail": "low",
    }})
    content.append({"type": "text", "text": f"[Frame at {format_time(kf.timestamp)}]"})
return content
```

`HighlightResult` dataclass에 `clips` 필드 추가:
```python
@dataclass
class HighlightResult:
    start_time: float       # 첫 클립 start (하위 호환)
    end_time: float         # 마지막 클립 end (하위 호환)
    title: str
    description: str
    score: float
    clips: list[dict] | None = None  # [{"start": 30, "end": 45}, ...]
```

### 3.6 `services/video_processor.py` — 파이프라인 확장

`_analyze_video` 메서드에 Step 3~5 추가:

```python
# Step 3: 키프레임 추출 (50-55%)
keyframes = await self._keyframe_extractor.extract(video_path, keyframe_dir)

# Step 4: 오디오 에너지 분석 (55-58%)
audio_hotspots = await self._audio_analyzer.analyze(audio_path)

# Step 5: 장면 전환 감지 (58-60%)
scene_changes = await self._scene_detector.detect(video_path)

# Step 6: 멀티모달 하이라이트 분석 (60-90%)
highlights = await self._highlight_analyzer.analyze_multimodal(
    transcript, keyframes, audio_hotspots, scene_changes, duration,
)
```

`VideoProcessor.__init__`에 새 서비스 추가:
```python
self._keyframe_extractor = KeyframeExtractor()
self._audio_analyzer = AudioAnalyzer()
self._scene_detector = SceneDetector()
```

DB 저장 시 clips 포함:
```python
highlights_data = [{
    "start_time": h.start_time,
    "end_time": h.end_time,
    "title": h.title,
    "description": h.description,
    "score": h.score,
    "clips": h.clips,
} for h in highlights]
```

### 3.7 `infrastructure/repository.py` — clips 저장

`create_batch`에서 clips 처리:
```python
highlight = Highlight(
    video_id=video_id,
    start_time=data["start_time"],
    end_time=data["end_time"],
    title=data["title"],
    description=data["description"],
    score=data["score"],
    clips=data.get("clips"),  # JSON 컬럼에 자동 직렬화
)
```

### 3.8 `services/export_processor.py` — concat Export

`process_export`에서 clips가 있으면 concat 필터 사용:

```python
async def process_export(self, job: ExportJob) -> ExportJob:
    # ... existing validation ...

    if job.layout == "shortform":
        if job.clips and len(job.clips) > 1:
            cmd = self._build_shortform_concat_cmd(...)
        else:
            cmd = self._build_shortform_cmd(...)
    else:
        if job.clips and len(job.clips) > 1:
            cmd = self._build_concat_cmd(...)
        else:
            cmd = [...existing original cmd...]
```

`_build_concat_cmd` (원본 비율 concat):
```python
def _build_concat_cmd(self, input_path, output_path, clips):
    """서브클립 concat FFmpeg 커맨드 (원본 비율)"""
    n = len(clips)
    filter_parts = []
    for i, clip in enumerate(clips):
        filter_parts.append(
            f"[0:v]trim=start={clip['start']}:end={clip['end']},"
            f"setpts=PTS-STARTPTS[v{i}];"
            f"[0:a]atrim=start={clip['start']}:end={clip['end']},"
            f"asetpts=PTS-STARTPTS[a{i}]"
        )
    streams = "".join(f"[v{i}][a{i}]" for i in range(n))
    filter_parts.append(f"{streams}concat=n={n}:v=1:a=1[outv][outa]")
    filter_complex = ";".join(filter_parts)

    return [
        "ffmpeg", "-y", "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-c:a", "aac",
        "-preset", "fast", "-crf", "23",
        "-movflags", "+faststart", output_path,
    ]
```

`_build_shortform_concat_cmd`는 concat 후 숏폼 레이아웃 적용 (2-pass filter).

ExportJob에 `clips` 필드 추가:
```python
class ExportJob:
    def __init__(self, ..., clips: list[dict] | None = None):
        self.clips = clips
```

`api/highlights.py`에서 export 시 clips 전달:
```python
job = await export_processor.create_export_job(
    highlight_id=highlight_id,
    video_path=video_path or "",
    start_time=highlight.start_time,
    end_time=highlight.end_time,
    layout=export_request.layout.value,
    clips=highlight.clips,  # JSON에서 자동 역직렬화된 list[dict]
)
```

### 3.9 Frontend Changes

**`types/index.ts`:**
```typescript
export interface Highlight {
  id: number;
  startTime: number;
  endTime: number;
  title: string;
  description: string;
  score: number;
  thumbnailUrl?: string;
  clips?: { start: number; end: number }[];  // NEW
}
```

**`HighlightCard.tsx`** — clips 정보 표시:
```tsx
{highlight.clips && highlight.clips.length > 1 && (
  <span className="text-xs text-violet-400">
    {highlight.clips.length}개 클립 편집
  </span>
)}
```

**`page.tsx`** — highlights 매핑에 clips 추가:
```typescript
setHighlights(data.highlights.map((h) => ({
  // ... existing fields ...
  clips: h.clips || undefined,
})));
```

---

## 4. Verification Items

| ID | Category | Verification |
|----|----------|-------------|
| V-01 | Keyframe | FFmpeg으로 10초 간격 JPEG 추출 + base64 인코딩 |
| V-02 | Keyframe | max_count 초과 시 interval 자동 조절 |
| V-03 | Audio | FFmpeg astats로 RMS 에너지 추출 |
| V-04 | Audio | 볼륨 급상승 핫스팟 식별 |
| V-05 | Scene | FFmpeg scene detect로 전환 시점 추출 |
| V-06 | GPT | 멀티모달 메시지에 텍스트+이미지+핫스팟+장면전환 포함 |
| V-07 | GPT | 응답이 clips 배열 포함 JSON 형태 |
| V-08 | DB | Highlight.clips JSON 컬럼 저장/조회 |
| V-09 | Export | 단일 클립 → 기존 방식 동작 |
| V-10 | Export | 다중 클립 → concat 필터로 이어붙이기 |
| V-11 | Export | 다중 클립 + shortform → concat + 9:16 레이아웃 |
| V-12 | Frontend | clips 정보 표시 (클립 수) |
| V-13 | Fallback | GPT-4o 사용 불가 시 기존 텍스트 분석 fallback |

---

## 5. Implementation Order

1. [ ] `core/config.py` — 멀티모달 설정 추가
2. [ ] `core/constants.py` — 멀티모달 프롬프트 추가
3. [ ] `services/keyframe_extractor.py` — 키프레임 추출 (NEW)
4. [ ] `services/audio_analyzer.py` — 오디오 에너지 분석 (NEW)
5. [ ] `services/scene_detector.py` — 장면 전환 감지 (NEW)
6. [ ] `services/highlight_analyzer.py` — analyze_multimodal 메서드
7. [ ] `infrastructure/models.py` — clips 컬럼 추가
8. [ ] `models/schemas.py` — ClipSegment, HighlightResponse clips
9. [ ] `infrastructure/repository.py` — clips 저장
10. [ ] `services/video_processor.py` — 파이프라인 확장
11. [ ] `services/export_processor.py` — concat Export + clips 필드
12. [ ] `api/highlights.py` — export 시 clips 전달
13. [ ] Frontend types/HighlightCard/page.tsx — clips 표시

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-08 | Initial draft | Claude |
