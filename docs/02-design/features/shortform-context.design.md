# shortform-context Design Document

> **Summary**: 숏폼 다운로드 영상에 맥락 구간 포함 — 상세 설계
>
> **Project**: Shortify
> **Version**: 0.4.1
> **Date**: 2026-03-09
> **Status**: Draft
> **Plan Reference**: `docs/01-plan/features/shortform-context.plan.md`

---

## 1. Implementation Design

### 1.1 CTX-04: config.py 설정 추가

**변경 파일**: `backend/src/core/config.py`

**변경 위치**: `# Highlight quality improvements` 섹션 (line 38~41) 뒤에 추가

```python
    # Shortform context
    context_padding: float = 3.0
    highlight_min_duration: int = 30
    highlight_max_duration: int = 55
```

---

### 1.2 CTX-01: GPT 프롬프트 맥락 지시

**변경 파일**: `backend/src/core/constants.py`

**변경 위치**: `MULTIMODAL_SYSTEM_PROMPT` (line 129~156)

#### 1.2.1 Editing rules 섹션 수정

현재 `- Total highlight duration: 15-60 seconds` (line 147)을 변경:

```python
# 현재
- Total highlight duration: 15-60 seconds

# 변경
- Total highlight duration: 30-55 seconds. Aim for a complete mini-narrative.
```

#### 1.2.2 Hook-first 규칙 수정

현재 (line 153):
```
- **Hook-first editing**: ... Structure: [Hook] -> [Context] -> [Climax] -> [Outro]
```

교체:
```python
- **Hook-first with context**: The FIRST clip grabs attention (2-3 seconds), then IMMEDIATELY provide a setup/context clip (3-5 seconds) so the viewer understands the topic. Each highlight must be comprehensible WITHOUT watching the original video. The viewer should understand "what is being discussed" within the first 8 seconds. Structure: [Hook 2-3s] -> [Setup/Context 3-5s] -> [Key Content] -> [Wrap-up]
```

#### 1.2.3 전체 교체 후 MULTIMODAL_SYSTEM_PROMPT

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
- Total highlight duration: 30-55 seconds. Aim for a complete mini-narrative.
- Clips must not overlap across highlights
- Score reflects importance (0.0-1.0)
- Title should be concise (under 20 characters)
- Description should explain why this segment is valuable (under 50 characters)
- Respond in the same language as the transcript
- **Hook-first with context**: The FIRST clip grabs attention (2-3 seconds), then IMMEDIATELY provide a setup/context clip (3-5 seconds) so the viewer understands the topic. Each highlight must be comprehensible WITHOUT watching the original video. The viewer should understand "what is being discussed" within the first 8 seconds. Structure: [Hook 2-3s] -> [Setup/Context 3-5s] -> [Key Content] -> [Wrap-up]
- **Pacing control**: Alternate between high-energy peaks and brief 2-3 second breathing moments. Don't pack 60 seconds of non-stop intensity — rhythm keeps viewers engaged longer than constant peaks.
- Avoid consecutive clips from the same scene unless energy builds progressively toward a climax.
- Return a JSON object with a "highlights" key containing an array"""
```

---

### 1.3 CTX-02 + CTX-03: 컨텍스트 패딩 + 길이 조절

**변경 파일**: `backend/src/services/highlight_analyzer.py`

#### 1.3.1 새 메서드: `_add_context_padding()`

문장 경계 스냅(`_snap_clips_to_sentences`) 바로 뒤에 추가:

```python
def _add_context_padding(
    self,
    clips: list[dict],
    transcript: TranscriptionResult,
    duration: float,
    padding: float = 3.0,
    max_total: int = 55,
) -> list[dict]:
    """각 클립 앞에 맥락 패딩 추가 (STT 세그먼트 경계 기준)"""
    if not transcript.segments or padding <= 0:
        return clips

    seg_starts = [seg.start for seg in transcript.segments]

    padded = []
    for clip in clips:
        new_start = clip["start"] - padding
        new_start = max(0.0, new_start)

        # STT 세그먼트 시작점으로 스냅 (문장 시작부터 포함)
        best = min(seg_starts, key=lambda b: abs(b - new_start))
        if best <= clip["start"] and abs(best - new_start) <= padding + 1:
            new_start = best

        new_start = max(0.0, new_start)
        padded.append({"start": new_start, "end": clip["end"]})

    # 인접 클립 겹침 제거 (뒤 클립 start를 앞 클립 end로 조정)
    for i in range(1, len(padded)):
        if padded[i]["start"] < padded[i - 1]["end"]:
            padded[i]["start"] = padded[i - 1]["end"]

    # 겹침 조정 후 최소 길이 미달 클립 제거
    padded = [c for c in padded if c["end"] - c["start"] >= 2.0]

    # 총 길이가 max_total 초과 시 패딩을 비례 축소
    total = sum(c["end"] - c["start"] for c in padded)
    if total > max_total:
        excess = total - max_total
        # 원래 클립 대비 추가된 패딩량 계산
        padding_amounts = []
        for i, (p, orig) in enumerate(zip(padded, clips)):
            added = orig["start"] - p["start"]
            padding_amounts.append(max(0.0, added))
        total_padding = sum(padding_amounts)

        if total_padding > 0:
            # 패딩을 비례적으로 축소
            ratio = max(0.0, (total_padding - excess) / total_padding)
            for i, (p, orig) in enumerate(zip(padded, clips)):
                added = orig["start"] - p["start"]
                if added > 0:
                    new_added = added * ratio
                    p["start"] = orig["start"] - new_added
                    p["start"] = max(0.0, p["start"])

    return padded
```

#### 1.3.2 `_parse_multimodal_response()` 수정

현재 코드 (line 324~338):
```python
            # Snap to sentence boundaries
            if transcript:
                settings = get_settings()
                valid_clips = self._snap_clips_to_sentences(
                    valid_clips, transcript, settings.snap_tolerance,
                )

            # Total duration check (15-60s)
            total_dur = sum(c["end"] - c["start"] for c in valid_clips)
            if total_dur < 15:
                # Extend last clip
                deficit = 15 - total_dur
                valid_clips[-1]["end"] = min(
                    valid_clips[-1]["end"] + deficit, duration
                )
```

변경 후:
```python
            # Snap to sentence boundaries
            if transcript:
                settings = get_settings()
                valid_clips = self._snap_clips_to_sentences(
                    valid_clips, transcript, settings.snap_tolerance,
                )

                # Add context padding
                valid_clips = self._add_context_padding(
                    valid_clips, transcript, duration,
                    padding=settings.context_padding,
                    max_total=settings.highlight_max_duration,
                )

            # Total duration check
            settings = get_settings()
            min_dur = settings.highlight_min_duration
            total_dur = sum(c["end"] - c["start"] for c in valid_clips)
            if total_dur < min_dur:
                # Extend last clip to meet minimum
                deficit = min_dur - total_dur
                valid_clips[-1]["end"] = min(
                    valid_clips[-1]["end"] + deficit, duration
                )
```

**핵심 변경**:
1. 스냅 후 `_add_context_padding()` 호출 추가
2. 하드코딩된 `15`를 `settings.highlight_min_duration`으로 교체

---

## 2. 처리 흐름 (변경 후)

```
GPT-4o 응답 (30~55초 목표 프롬프트)
  |
  v
클립 검증 (기존: start/end 클램핑, 3초 미만 제거)
  |
  v
문장 경계 스냅 (기존 IMP-01: STT 세그먼트 경계로 보정)
  |
  v
컨텍스트 패딩 (NEW)
  |- 각 클립 start를 3초 앞으로 확장
  |- STT 세그먼트 시작점으로 스냅 (문장 시작부터 포함)
  |- 인접 클립 겹침 제거
  |- 총 길이 > 55초면 패딩 비례 축소
  |
  v
총 길이 조절 (변경)
  |- < 30초: 마지막 클립 확장
  |- > 55초: 이미 패딩에서 처리됨
  |
  v
DB 저장 → Export 시 xfade concat
```

---

## 3. Implementation Order

```
1. config.py            — context_padding, highlight_min/max_duration 추가
2. constants.py          — 프롬프트 수정 (30~55초 + Hook-first with context)
3. highlight_analyzer.py — _add_context_padding() + _parse_multimodal_response 수정
```

---

## 4. Backward Compatibility

| Scenario | Behavior |
|----------|----------|
| `context_padding=0` | 패딩 비활성, 기존 동작 |
| transcript=None (fallback 분석) | 스냅/패딩 모두 스킵, 기존 동작 |
| 단일 클립 (clips=None) | `_add_context_padding`이 1개 클립에도 동작, start만 확장 |
| GPT가 이미 30초+ 클립 반환 | 패딩 적용 → 55초 초과 시 패딩 축소 → 최대 55초 |

---

## 5. Error Handling

| Failure Point | Handling |
|---------------|----------|
| `seg_starts` 빈 리스트 | 패딩 스냅 스킵, 시간 기반 패딩만 적용 |
| 패딩 후 클립 길이 < 2초 | 해당 클립 제거 |
| 패딩 축소 후에도 > 55초 | GPT가 이미 긴 클립 반환한 경우, 초과 허용 (60초 상한은 기존 export에서 처리) |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial design | Claude |
