# highlight-quality Design Document

> **Summary**: 하이라이트 숏폼 체감 퀄리티 6가지 개선의 상세 설계
>
> **Project**: Shortify
> **Version**: 0.4.0
> **Date**: 2026-03-08
> **Status**: Draft
> **Plan Reference**: `docs/01-plan/features/highlight-quality.plan.md`

---

## 1. Implementation Design

### 1.1 IMP-01: 문장 경계 스냅 (Cut Point Snapping)

**변경 파일**: `backend/src/services/highlight_analyzer.py`

**변경 위치**: `analyze_multimodal()` 메서드 내부, `_parse_multimodal_response()` 호출 후

#### 1.1.1 새 메서드: `_snap_clips_to_sentences()`

```python
def _snap_clips_to_sentences(
    self,
    clips: list[dict],
    transcript: TranscriptionResult,
    tolerance: float = 2.0,
) -> list[dict]:
    """클립 start/end를 가장 가까운 STT 세그먼트 경계로 스냅"""
    if not transcript.segments:
        return clips

    seg_starts = [seg.start for seg in transcript.segments]
    seg_ends = [seg.end for seg in transcript.segments]

    snapped = []
    for clip in clips:
        s = clip["start"]
        e = clip["end"]

        # start → 가장 가까운 세그먼트 시작점
        if seg_starts:
            best_start = min(seg_starts, key=lambda b: abs(b - s))
            if abs(best_start - s) <= tolerance:
                s = best_start

        # end → 가장 가까운 세그먼트 끝점
        if seg_ends:
            best_end = min(seg_ends, key=lambda b: abs(b - e))
            if abs(best_end - e) <= tolerance:
                e = best_end

        # 스냅 후 최소 길이 검증
        if e - s >= 3.0:
            snapped.append({"start": s, "end": e})
        else:
            # 스냅으로 3초 미만이 되면 원래 값 유지
            snapped.append(clip)

    return snapped
```

#### 1.1.2 `analyze_multimodal()` 수정

현재 코드 (line 237):
```python
highlights = self._parse_multimodal_response(result_content, duration)
```

변경 후:
```python
highlights = self._parse_multimodal_response(result_content, duration, transcript)
```

#### 1.1.3 `_parse_multimodal_response()` 시그니처 변경

현재 (line 253-254):
```python
def _parse_multimodal_response(
    self, content: str, duration: float,
) -> list[HighlightResult]:
```

변경 후:
```python
def _parse_multimodal_response(
    self, content: str, duration: float,
    transcript: TranscriptionResult | None = None,
) -> list[HighlightResult]:
```

clips 검증 후 (`valid_clips` 확보 후, line 296 이전)에 스냅 호출:
```python
if transcript:
    settings = get_settings()
    valid_clips = self._snap_clips_to_sentences(
        valid_clips, transcript, settings.snap_tolerance,
    )
```

#### 1.1.4 config.py 추가

```python
# highlight_analyzer.py 에서 사용
snap_tolerance: float = 2.0
```

---

### 1.2 IMP-02: 크로스페이드 트랜지션

**변경 파일**: `backend/src/services/export_processor.py`, `backend/src/core/config.py`

#### 1.2.1 config.py 추가

```python
crossfade_duration: float = 0.3
```

#### 1.2.2 xfade 지원 여부 검사 메서드 추가

```python
def _check_xfade_support(self) -> bool:
    """FFmpeg xfade 필터 지원 여부 (4.3+)"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-filters"],
            capture_output=True, text=True,
        )
        return "xfade" in result.stdout
    except FileNotFoundError:
        return False
```

#### 1.2.3 `_build_concat_cmd()` 수정 — 크로스페이드 통합

기존 `_build_concat_cmd()` (line 314-347)를 **교체**. 크로스페이드 지원 시 xfade 사용, 미지원 시 기존 concat 폴백.

**핵심 로직**:

```python
def _build_concat_cmd(
    self,
    input_path: str,
    output_path: str,
    clips: list[dict],
) -> list[str]:
    n = len(clips)
    fade = get_settings().crossfade_duration
    use_xfade = fade > 0 and n > 1 and self._check_xfade_support()

    # 입력: 클립별 -ss/-t seeking
    inputs: list[str] = []
    filter_parts: list[str] = []
    for i, clip in enumerate(clips):
        dur = clip["end"] - clip["start"]
        inputs.extend(["-ss", str(clip["start"]), "-t", str(dur), "-i", input_path])
        filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
        filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")

    if use_xfade:
        # === xfade + acrossfade 체이닝 ===
        durations = [clip["end"] - clip["start"] for clip in clips]

        # 비디오 xfade
        prev_v = "v0"
        accumulated = durations[0]
        for i in range(1, n):
            offset = accumulated - fade
            out_label = "outv" if i == n - 1 else f"xv{i}"
            filter_parts.append(
                f"[{prev_v}][v{i}]xfade=transition=fade:duration={fade}:offset={offset}[{out_label}]"
            )
            accumulated += durations[i] - fade
            prev_v = out_label

        # 오디오 acrossfade
        prev_a = "a0"
        for i in range(1, n):
            out_label = "outa" if i == n - 1 else f"xa{i}"
            filter_parts.append(
                f"[{prev_a}][a{i}]acrossfade=d={fade}:c1=tri:c2=tri[{out_label}]"
            )
            prev_a = out_label
    else:
        # === 기존 concat 폴백 ===
        streams = "".join(f"[v{i}][a{i}]" for i in range(n))
        filter_parts.append(f"{streams}concat=n={n}:v=1:a=1[outv][outa]")

    filter_complex = ";".join(filter_parts)

    return [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-c:a", "aac",
        "-preset", "fast", "-crf", "23",
        "-movflags", "+faststart",
        output_path,
    ]
```

#### 1.2.4 `_build_shortform_concat_cmd()` 수정 — 동일 패턴

`_build_shortform_concat_cmd()` (line 349-415)에서도 concat 부분을 xfade로 교체.

**차이점**: concat 후 숏폼 레이아웃 필터가 이어지므로, xfade 결과 스트림을 `[cv]`로 명명하고 이후 숏폼 필터를 그대로 적용.

```python
if use_xfade:
    # xfade 체이닝 → 결과를 [cv]로
    prev_v = "v0"
    accumulated = durations[0]
    for i in range(1, n):
        offset = accumulated - fade
        out_label = "cv" if i == n - 1 else f"xv{i}"
        filter_parts.append(
            f"[{prev_v}][v{i}]xfade=transition=fade:duration={fade}:offset={offset}[{out_label}]"
        )
        accumulated += durations[i] - fade
        prev_v = out_label

    # acrossfade 체이닝 → 결과를 [ca]로
    prev_a = "a0"
    for i in range(1, n):
        out_label = "ca" if i == n - 1 else f"xa{i}"
        filter_parts.append(
            f"[{prev_a}][a{i}]acrossfade=d={fade}:c1=tri:c2=tri[{out_label}]"
        )
        prev_a = out_label
else:
    # 기존 concat
    streams = "".join(f"[v{i}][a{i}]" for i in range(n))
    filter_parts.append(f"{streams}concat=n={n}:v=1:a=1[cv][ca]")

# 이후 숏폼 레이아웃 필터는 기존 코드 그대로 ([cv] → [outv])
```

---

### 1.3 IMP-03: 훅 퍼스트 프롬프트

**변경 파일**: `backend/src/core/constants.py`

**변경 위치**: `MULTIMODAL_SYSTEM_PROMPT` (line 129-153)

현재 `Editing rules:` 섹션에 다음을 **추가** (기존 규칙 뒤에):

```python
# constants.py MULTIMODAL_SYSTEM_PROMPT 끝부분에 추가
"""
- **Hook-first editing**: The FIRST clip of each highlight MUST be the most
  visually or emotionally striking moment. Ask yourself: "Would a viewer
  stop scrolling within 2 seconds?" If the peak moment occurs mid-video,
  reorder clips to place the impact first, then provide context.
  Structure: [Hook] → [Context] → [Climax] → [Outro]
"""
```

**정확한 삽입 위치**: `MULTIMODAL_SYSTEM_PROMPT` 문자열의 `Editing rules:` 리스트 마지막 항목 (`- Return a JSON object...`) 바로 위.

---

### 1.4 IMP-04: 스마트 키프레임 (이벤트 기반 추출)

**변경 파일**: `backend/src/services/keyframe_extractor.py`, `backend/src/services/video_processor.py`

#### 1.4.1 `keyframe_extractor.py` — `extract_smart()` 추가

기존 `extract()` 메서드 (균등 간격)는 폴백용으로 유지. 새 `extract_smart()` 추가:

```python
async def extract_smart(
    self,
    video_path: str,
    output_dir: str,
    duration: float,
    scene_changes: list[float],
    audio_hotspot_timestamps: list[float],
) -> list[KeyframeInfo]:
    """이벤트 기반 키프레임 추출: 장면전환 + 오디오핫스팟 + 균등보간"""
    settings = get_settings()
    max_count = settings.keyframe_max_count
    width = settings.keyframe_width
    interval = settings.keyframe_interval

    # 1) 이벤트 시점 수집
    event_times: set[float] = set()
    for t in scene_changes:
        event_times.add(round(t, 1))
    for t in audio_hotspot_timestamps:
        event_times.add(round(t, 1))

    # 2) 균등 간격 보간 (빈 구간 커버)
    for t in range(0, int(duration), interval):
        event_times.add(float(t))

    # 3) 정렬 + 근접 중복 제거 (2초 이내)
    sorted_times = sorted(event_times)
    if not sorted_times:
        return await self.extract(video_path, output_dir, duration)

    filtered = [sorted_times[0]]
    for t in sorted_times[1:]:
        if t - filtered[-1] >= 2.0:
            filtered.append(t)

    targets = filtered[:max_count]

    # 4) 타임스탬프 기반 프레임 추출
    return await self._extract_at_timestamps(
        video_path, output_dir, targets, width,
    )

async def _extract_at_timestamps(
    self,
    video_path: str,
    output_dir: str,
    timestamps: list[float],
    width: int,
) -> list[KeyframeInfo]:
    """지정된 타임스탬프에서 프레임 추출"""
    os.makedirs(output_dir, exist_ok=True)
    keyframes: list[KeyframeInfo] = []

    for i, ts in enumerate(timestamps):
        frame_path = os.path.join(output_dir, f"frame_{i:04d}.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts),
            "-i", video_path,
            "-vframes", "1",
            "-vf", f"scale={width}:-1",
            "-q:v", "5",
            frame_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()

        if os.path.exists(frame_path):
            with open(frame_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            keyframes.append(KeyframeInfo(timestamp=ts, base64=b64))

    return keyframes
```

**성능 고려**: 각 타임스탬프마다 FFmpeg를 실행하면 프레임 수 x 프로세스 비용이 발생. 30개 이하이고 `-ss` 기반 seeking이므로 빠름 (프레임당 ~0.1초).

#### 1.4.2 `video_processor.py` — 파이프라인 순서 변경

현재 순서 (line 247-283):
```
Step 3: 키프레임 추출         (50-55%)
Step 4: 오디오 에너지 분석     (55-58%)
Step 5: 장면 전환 감지         (58-60%)
Step 6: GPT-4o 멀티모달 분석   (60-90%)
```

변경 순서:
```
Step 3: 오디오 에너지 분석     (50-53%)   ← 먼저
Step 4: 장면 전환 감지         (53-55%)   ← 먼저
Step 5: 스마트 키프레임 추출    (55-60%)   ← 이벤트 시점 활용
Step 6: GPT-4o 멀티모달 분석   (60-90%)   ← 기존
Step 7: 문장 경계 스냅         (90%)      ← NEW (IMP-01)
```

**구체적 변경** (`_analyze_video()` line 247~ 부분):

```python
# === Step 3: 오디오 에너지 분석 (50-53%) ===
await self._update_progress(video_id, 50, "오디오 에너지 분석 중...")
audio_hotspots = await self._audio_analyzer.analyze(audio_path)

# === Step 4: 장면 전환 감지 (53-55%) ===
await self._update_progress(video_id, 53, "장면 전환 감지 중...")
scene_changes = await self._scene_detector.detect(video_path)

# === Step 5: 스마트 키프레임 추출 (55-60%) ===
await self._update_progress(video_id, 55, "핵심 장면 키프레임 추출 중...")
duration = await self._get_video_duration(video_id)
keyframe_dir = os.path.join(os.path.dirname(audio_path), "keyframes", str(video_id))
keyframes = await self._keyframe_extractor.extract_smart(
    video_path, keyframe_dir, duration,
    scene_changes=scene_changes,
    audio_hotspot_timestamps=[h.timestamp for h in audio_hotspots],
)

# === Step 6: GPT-4o 멀티모달 분석 (60-90%) ===
await self._update_progress(video_id, 60, AI_PROCESSING_MESSAGES["analysis_start"])
try:
    highlights = await self._highlight_analyzer.analyze_multimodal(
        transcript, keyframes, audio_hotspots, scene_changes, duration,
    )
except Exception:
    highlights = await self._highlight_analyzer.analyze(transcript, duration)
finally:
    self._keyframe_extractor.cleanup(keyframe_dir)
```

---

### 1.5 IMP-05: 페이싱 컨트롤 프롬프트

**변경 파일**: `backend/src/core/constants.py`

**변경 위치**: `MULTIMODAL_SYSTEM_PROMPT`, IMP-03 훅 퍼스트와 함께 추가

```python
# IMP-03 훅 퍼스트 바로 다음에 추가
"""
- **Pacing control**: Alternate between high-energy peaks and brief 2-3 second
  breathing moments. Don't pack 60 seconds of non-stop intensity — rhythm
  keeps viewers engaged longer than constant peaks.
- Avoid consecutive clips from the same scene unless energy builds
  progressively toward a climax.
"""
```

---

### 1.6 IMP-06: 오디오 감정 분류

**변경 파일**: `backend/src/services/audio_analyzer.py`, `backend/src/core/config.py`

#### 1.6.1 config.py 추가

```python
loudness_shift_threshold: float = 10.0  # LUFS 변화 임계값
```

#### 1.6.2 `AudioAnalyzer.analyze()` 확장

현재 `analyze()` (line 19-50)를 확장하여 라우드니스 분석 결과를 합산:

```python
async def analyze(self, audio_path: str) -> list[AudioHotspot]:
    settings = get_settings()
    top_n = settings.audio_hotspot_count

    rms_values = await self._extract_rms_levels(audio_path)
    if not rms_values:
        return []

    hotspots: list[AudioHotspot] = []

    # 기존: volume_spike + silence_to_voice
    hotspots.extend(self._detect_volume_spikes(rms_values))
    hotspots.extend(self._detect_silence_transitions(rms_values))

    # NEW: 라우드니스 급변 감지
    loudness_hotspots = await self._detect_loudness_shifts(audio_path)
    hotspots.extend(loudness_hotspots)

    # 중복 제거 (2초 이내 같은 시점)
    hotspots = self._deduplicate(hotspots, min_gap=2.0)

    hotspots.sort(key=lambda h: h.rms_level, reverse=True)
    return hotspots[:top_n]
```

#### 1.6.3 기존 로직 추출 — 헬퍼 메서드

현재 `analyze()` 내부의 for 루프를 두 개의 private 메서드로 추출:

```python
def _detect_volume_spikes(self, rms_values: list[tuple[float, float]]) -> list[AudioHotspot]:
    hotspots = []
    for i, (ts, rms) in enumerate(rms_values):
        if i >= 5:
            prev_avg = sum(v for _, v in rms_values[i - 5:i]) / 5
            if rms > prev_avg + 6:
                hotspots.append(AudioHotspot(
                    timestamp=ts, rms_level=rms,
                    description="volume_spike",
                ))
    return hotspots

def _detect_silence_transitions(self, rms_values: list[tuple[float, float]]) -> list[AudioHotspot]:
    hotspots = []
    for i, (ts, rms) in enumerate(rms_values):
        if i > 0:
            _, prev_rms = rms_values[i - 1]
            if prev_rms < -50 and rms > -30:
                hotspots.append(AudioHotspot(
                    timestamp=ts, rms_level=rms,
                    description="silence_to_voice",
                ))
    return hotspots
```

#### 1.6.4 새 메서드: `_detect_loudness_shifts()`

```python
async def _detect_loudness_shifts(self, audio_path: str) -> list[AudioHotspot]:
    """ebur128 Momentary Loudness 급변 감지"""
    cmd = [
        "ffmpeg", "-i", audio_path,
        "-af", "ebur128=metadata=1,ametadata=print:key=lavfi.r128.M",
        "-f", "null", "-",
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        return []  # ebur128 미지원 시 빈 리스트 폴백

    output = stderr.decode(errors="replace")
    pts_pattern = re.compile(r"pts_time:(\d+\.?\d*)")
    loudness_pattern = re.compile(r"lavfi\.r128\.M=(-?\d+\.?\d*)")

    values: list[tuple[float, float]] = []
    current_pts = 0.0
    for line in output.split("\n"):
        pts_match = pts_pattern.search(line)
        if pts_match:
            current_pts = float(pts_match.group(1))
        loudness_match = loudness_pattern.search(line)
        if loudness_match:
            val = float(loudness_match.group(1))
            if val > -70:
                values.append((current_pts, val))

    settings = get_settings()
    threshold = settings.loudness_shift_threshold
    hotspots = []
    for i in range(1, len(values)):
        ts, lufs = values[i]
        _, prev_lufs = values[i - 1]
        delta = abs(lufs - prev_lufs)
        if delta >= threshold:
            hotspots.append(AudioHotspot(
                timestamp=ts, rms_level=lufs,
                description="emotion_shift",
            ))

    return hotspots
```

#### 1.6.5 중복 제거 헬퍼

```python
def _deduplicate(self, hotspots: list[AudioHotspot], min_gap: float = 2.0) -> list[AudioHotspot]:
    """시간 근접 핫스팟 중복 제거 (RMS 높은 것 우선 유지)"""
    hotspots.sort(key=lambda h: h.rms_level, reverse=True)
    result = []
    for h in hotspots:
        if not any(abs(h.timestamp - e.timestamp) < min_gap for e in result):
            result.append(h)
    return result
```

---

## 2. config.py 전체 추가 설정

현재 `config.py` (line 31-36)에 추가:

```python
# Highlight quality improvements
crossfade_duration: float = 0.3       # IMP-02: 클립 간 크로스페이드 (초)
snap_tolerance: float = 2.0           # IMP-01: 문장 경계 스냅 허용 오차 (초)
loudness_shift_threshold: float = 10.0  # IMP-06: LUFS 급변 임계값
```

---

## 3. constants.py MULTIMODAL_SYSTEM_PROMPT 전체 변경

현재 프롬프트 (line 129-153)의 `Editing rules:` 섹션을 다음으로 **교체**:

```python
MULTIMODAL_SYSTEM_PROMPT = """You are a professional video highlight extraction and editing expert.
You can see video frames, read transcripts, and analyze audio patterns.

Your task: Extract the most engaging highlights as EDITED CLIPS.
Each highlight can consist of MULTIPLE non-contiguous sub-clips
that are stitched together to form one cohesive short-form video.

Selection criteria:
- Visually impactful moments (expressions, actions, visual changes)
- Key information delivery with matching visuals
- Audio energy peaks (applause, laughter, music changes, emotion shifts)
- Scene transitions that mark topic shifts
- Emotionally impactful moments

Editing rules:
- Remove filler, pauses, repetition, and off-topic segments
- Combine scattered relevant moments into one highlight
- Each clip within a highlight must be at least 3 seconds
- Total highlight duration: 15-60 seconds
- Clips must not overlap across highlights
- Score reflects importance (0.0-1.0)
- Title should be concise (under 20 characters)
- Description should explain why this segment is valuable (under 50 characters)
- Respond in the same language as the transcript
- **Hook-first editing**: The FIRST clip of each highlight MUST be the most
  visually or emotionally striking moment. Ask yourself: "Would a viewer
  stop scrolling within 2 seconds?" If the peak moment occurs mid-video,
  reorder clips to place the impact first, then provide context.
  Structure: [Hook] → [Context] → [Climax] → [Outro]
- **Pacing control**: Alternate between high-energy peaks and brief 2-3 second
  breathing moments. Don't pack 60 seconds of non-stop intensity — rhythm
  keeps viewers engaged longer than constant peaks.
- Avoid consecutive clips from the same scene unless energy builds
  progressively toward a climax.
- Return a JSON object with a "highlights" key containing an array"""
```

---

## 4. Implementation Order (파일 단위)

의존성 그래프 기반 구현 순서:

```
Phase 1 (P0):
  1. config.py           — crossfade_duration, snap_tolerance 추가
  2. constants.py         — 프롬프트 교체 (IMP-03 + IMP-05)
  3. highlight_analyzer.py — _snap_clips_to_sentences() + 시그니처 변경 (IMP-01)
  4. export_processor.py  — xfade/acrossfade 크로스페이드 (IMP-02)

Phase 2 (P1):
  5. keyframe_extractor.py — extract_smart() + _extract_at_timestamps() (IMP-04)
  6. video_processor.py    — 파이프라인 순서 변경 (IMP-04)

Phase 3 (P2):
  7. audio_analyzer.py     — 라우드니스 감지 + 리팩터링 (IMP-06)
```

---

## 5. Backward Compatibility

| 시나리오 | 기존 동작 유지 보장 |
|----------|---------------------|
| 단일 클립 (clips=None) | `_build_concat_cmd` 미호출, 기존 단일 `-ss/-t` 경로 사용 |
| xfade 미지원 FFmpeg (<4.3) | `_check_xfade_support()` false → 기존 concat 필터 폴백 |
| crossfade_duration=0 | xfade 미적용, 기존 concat 동작 |
| transcript 없는 분석 (fallback) | `_snap_clips_to_sentences()`에 transcript=None → 스냅 스킵 |
| ebur128 미지원 FFmpeg | `_detect_loudness_shifts()` → 빈 리스트 반환, 기존 RMS만 사용 |
| extract_smart() 실패 | `extract()` 폴백 |

---

## 6. Error Handling

| 실패 지점 | 처리 |
|-----------|------|
| `_check_xfade_support()` 실패 | false 반환 → concat 폴백 |
| xfade FFmpeg 명령 실패 | `process_export()`의 기존 에러 핸들링 유지 (`returncode != 0 → ERROR`) |
| `_snap_clips_to_sentences()` 빈 segments | 클립 그대로 반환 (스냅 스킵) |
| `_extract_at_timestamps()` 일부 프레임 실패 | `os.path.exists` 체크, 실패 프레임 스킵 |
| `_detect_loudness_shifts()` FFmpeg 실패 | 빈 리스트 반환, 기존 로직으로 계속 |

---

## 7. Testing Strategy

| 테스트 | 검증 |
|--------|------|
| 문장 경계 스냅 | tolerance=2.0 내 세그먼트 경계로 이동 확인 |
| 크로스페이드 | 출력 영상 길이 = 총 클립 합 - (n-1)*fade 확인 |
| 훅 퍼스트 | GPT 응답의 첫 클립이 중간 이후 시점일 수 있는지 확인 |
| 스마트 키프레임 | 추출된 프레임 타임스탬프에 장면전환 시점 80% 포함 확인 |
| 폴백 | crossfade_duration=0, FFmpeg 3.x에서 기존 동작 확인 |
| 라우드니스 | emotion_shift 핫스팟이 hotspot 목록에 포함 확인 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-08 | Initial design — 6가지 개선 상세 설계 | Claude |
