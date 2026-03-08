# highlight-quality Planning Document

> **Summary**: 하이라이트 숏폼의 체감 퀄리티 대폭 개선 — 문장 경계 스냅, 크로스페이드, 훅 퍼스트, 스마트 키프레임, 페이싱 컨트롤, 오디오 감정 분류
>
> **Project**: Shortify
> **Version**: 0.4.0
> **Date**: 2026-03-08
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 현재 멀티모달 하이라이트는 분석 소스는 다양하지만, 실제 출력 영상의 컷 포인트가 문장 중간에서 잘리고 클립 간 전환이 하드컷이라 부자연스럽고, 첫 장면이 밋밋해 시청 이탈이 높다 |
| **Solution** | 6가지 품질 개선 — (1) 클립 경계를 STT 세그먼트 경계로 스냅, (2) xfade/acrossfade로 자연스러운 전환, (3) 훅 퍼스트 프롬프트, (4) 이벤트 기반 스마트 키프레임, (5) 페이싱 컨트롤, (6) 라우드니스 기반 오디오 감정 분류 |
| **Function/UX Effect** | 말이 끊기지 않고, 장면 전환이 부드러우며, 첫 2초에 임팩트 있는 장면이 오고, 템포에 완급이 있는 프로 수준 숏폼이 자동 생성된다 |
| **Core Value** | "AI 프로 편집" — 컷 포인트, 트랜지션, 구성, 템포까지 자동 최적화하여 편집자 없이 시청 유지율 높은 숏폼 생성 |

---

## 1. Overview

### 1.1 Purpose

`multimodal-highlight` 기능이 "무엇을 추출할지"를 개선했다면, 이번 `highlight-quality`는 "추출한 것을 얼마나 자연스럽게 보여줄지"를 개선한다.

### 1.2 현재 약점 분석

| 약점 | 현상 | 영향 |
|------|------|------|
| 하드컷 전환 | 서브클립 간 뚝뚝 끊김 | 시청자가 편집 이음새를 느끼고 이탈 |
| 문장 중간 컷 | "그래서 이것은—" 에서 영상 끝 | 어색함, 내용 전달 실패 |
| 밋밋한 시작 | 하이라이트가 맥락 설명부터 시작 | 첫 2초 내 스크롤 이탈 |
| 균등 키프레임 | 10초 간격 기계적 추출 | GPT-4o가 핵심 장면 이미지를 못 봄 |
| 단조로운 템포 | 내내 고에너지 or 내내 설명 | 시청 피로, 중간 이탈 |
| 기본 오디오 분석 | RMS 스파이크만 감지 | 웃음, 박수, 감정 전환 놓침 |

### 1.3 개선 목표

```
현재:  [하드컷]——[하드컷]——[하드컷]   문장 중간에 잘림, 밋밋한 시작
개선:  [Hook!]~~fade~~[Peak]~~fade~~[Outro]   훅→절정→마무리, 자연스러운 전환
```

---

## 2. Scope

### 2.1 In Scope — 6가지 개선

| ID | 개선 | 변경 대상 | 우선순위 |
|----|------|-----------|----------|
| IMP-01 | 문장 경계 스냅 (Cut Point Snapping) | `highlight_analyzer.py` | P0 |
| IMP-02 | 크로스페이드 트랜지션 (xfade + acrossfade) | `export_processor.py` | P0 |
| IMP-03 | 훅 퍼스트 프롬프트 (Hook-First) | `constants.py` | P0 |
| IMP-04 | 스마트 키프레임 (이벤트 기반 추출) | `keyframe_extractor.py`, `video_processor.py` | P1 |
| IMP-05 | 페이싱 컨트롤 프롬프트 | `constants.py` | P1 |
| IMP-06 | 오디오 감정 분류 (라우드니스 + 스펙트럼) | `audio_analyzer.py` | P2 |

### 2.2 Out of Scope

- 사용자 수동 트랜지션 효과 선택 UI
- 자막 생성/오버레이 (별도 기능)
- BGM 자동 삽입
- AI 기반 썸네일 생성
- GPU 가속 인코딩

---

## 3. Requirements

### 3.1 Functional Requirements

#### IMP-01: 문장 경계 스냅

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | GPT-4o가 반환한 클립 start/end를 가장 가까운 STT 세그먼트 경계로 스냅한다 | High |
| FR-02 | 스냅 허용 범위(tolerance)는 기본 2.0초, config에서 조절 가능하다 | Medium |
| FR-03 | start는 세그먼트 시작점으로, end는 세그먼트 끝점으로 스냅한다 | High |
| FR-04 | 스냅 후에도 클립 최소 길이(3초) 검증을 유지한다 | High |

**구현 위치**: `highlight_analyzer.py` — `_parse_multimodal_response()` 후처리

**로직**:
```python
def _snap_to_sentence_boundary(self, clips, transcript, tolerance=2.0):
    seg_starts = [seg.start for seg in transcript.segments]
    seg_ends = [seg.end for seg in transcript.segments]

    for clip in clips:
        # start → 가장 가까운 세그먼트 시작점
        best = min(seg_starts, key=lambda b: abs(b - clip["start"]), default=clip["start"])
        if abs(best - clip["start"]) <= tolerance:
            clip["start"] = best

        # end → 가장 가까운 세그먼트 끝점
        best = min(seg_ends, key=lambda b: abs(b - clip["end"]), default=clip["end"])
        if abs(best - clip["end"]) <= tolerance:
            clip["end"] = best

    return clips
```

#### IMP-02: 크로스페이드 트랜지션

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-05 | 서브클립 2개 이상일 때 클립 간 xfade(비디오) + acrossfade(오디오)를 적용한다 | High |
| FR-06 | 기본 크로스페이드 길이는 0.3초, config에서 조절 가능하다 | Medium |
| FR-07 | 단일 클립(clips 없음)일 때는 기존 동작 유지한다 | High |
| FR-08 | 숏폼 레이아웃 + 멀티클립에도 크로스페이드가 적용된다 | High |
| FR-09 | 크로스페이드로 인한 총 길이 감소분을 계산에 반영한다 | Medium |

**구현 위치**: `export_processor.py` — `_build_concat_cmd()`, `_build_shortform_concat_cmd()` 교체

**FFmpeg 필터 체이닝**:
```
# 비디오: xfade 순차 체이닝
[v0][v1]xfade=transition=fade:duration=0.3:offset={d0-0.3}[xv1];
[xv1][v2]xfade=transition=fade:duration=0.3:offset={d0+d1-0.6}[outv]

# 오디오: acrossfade 순차 체이닝
[a0][a1]acrossfade=d=0.3:c1=tri:c2=tri[xa1];
[xa1][a2]acrossfade=d=0.3:c1=tri:c2=tri[outa]
```

#### IMP-03: 훅 퍼스트 프롬프트

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-10 | MULTIMODAL_SYSTEM_PROMPT에 "첫 클립은 가장 임팩트 있는 순간이어야 한다" 지시를 추가한다 | High |
| FR-11 | "시청자가 2초 이내에 스크롤을 멈출 만한 장면"을 첫 클립 기준으로 명시한다 | High |
| FR-12 | 원래 맥락 순서가 아닌, 임팩트 순 재배열을 허용하는 프롬프트를 추가한다 | Medium |

**프롬프트 추가 내용**:
```
- **Hook-first editing**: The first clip of each highlight MUST be the most
  visually or emotionally striking moment. Ask yourself: "Would a viewer
  stop scrolling within 2 seconds?" If the peak moment is in the middle,
  reorder clips to front-load the impact, then provide context after.
```

#### IMP-04: 스마트 키프레임

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-13 | 키프레임 추출을 균등 간격 대신 이벤트 기반(장면전환 + 오디오 핫스팟 + 보간)으로 변경한다 | High |
| FR-14 | 장면 전환 시점과 오디오 핫스팟 시점의 프레임을 우선 추출한다 | High |
| FR-15 | 이벤트 없는 구간은 기존 간격으로 보간하여 최소 커버리지를 보장한다 | Medium |
| FR-16 | 근접 중복 제거 (2초 이내)를 적용하고 max_count 상한을 유지한다 | Medium |
| FR-17 | `video_processor.py` 파이프라인 순서를 변경한다: 오디오 분석+장면 전환 → 키프레임 추출 | High |

**파이프라인 순서 변경**:
```
현재: STT → 키프레임 → 오디오분석 → 장면전환 → GPT-4o
개선: STT → 오디오분석 → 장면전환 → 스마트 키프레임 → GPT-4o
                                       ↑ 이벤트 시점 활용
```

**구현 위치**: `keyframe_extractor.py` — `extract_smart()` 메서드 추가

```python
async def extract_smart(self, video_path, output_dir, duration,
                        scene_changes, audio_hotspots) -> list[KeyframeInfo]:
    event_times = set()
    for t in scene_changes:
        event_times.add(round(t, 1))
    for h in audio_hotspots:
        event_times.add(round(h.timestamp, 1))

    # 보간: 빈 구간 커버
    for t in range(0, int(duration), self.interval):
        event_times.add(float(t))

    # 근접 중복 제거 (2초 이내)
    sorted_times = sorted(event_times)
    filtered = [sorted_times[0]]
    for t in sorted_times[1:]:
        if t - filtered[-1] >= 2.0:
            filtered.append(t)

    targets = filtered[:self.max_count]
    return await self._extract_at_timestamps(video_path, output_dir, targets)
```

#### IMP-05: 페이싱 컨트롤 프롬프트

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-18 | 프롬프트에 "고에너지와 호흡 구간을 번갈아 배치하라" 지시를 추가한다 | Medium |
| FR-19 | "같은 장면에서 연속 클립을 뽑지 말라" (에너지 빌드업 제외) 지시를 추가한다 | Medium |

**프롬프트 추가 내용**:
```
- **Pacing control**: Alternate between high-energy peaks and brief
  2-3 second breathing moments. Don't pack 60 seconds of non-stop
  intensity. Rhythm keeps viewers engaged longer than constant peaks.
- Avoid consecutive clips from the same scene unless energy builds
  progressively toward a climax.
```

#### IMP-06: 오디오 감정 분류

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-20 | FFmpeg `ebur128` 필터로 라우드니스 변화 속도(LRA)를 추출한다 | Medium |
| FR-21 | 라우드니스 급변 구간을 "감정 전환(emotion_shift)" 핫스팟으로 분류한다 | Medium |
| FR-22 | FFmpeg `showfreqs` 또는 스펙트럼 분석으로 광대역 노이즈(박수/웃음)를 감지한다 | Low |
| FR-23 | 기존 volume_spike, silence_to_voice에 emotion_shift, audience_reaction 타입을 추가한다 | Medium |
| FR-24 | 핫스팟 description을 GPT에 전달할 때 타입별 의미를 포함한다 | Medium |

**구현 위치**: `audio_analyzer.py` 확장

```python
async def _extract_loudness_changes(self, audio_path: str) -> list[AudioHotspot]:
    """ebur128 필터로 라우드니스 변화 속도 분석"""
    cmd = [
        "ffmpeg", "-i", audio_path,
        "-af", "ebur128=metadata=1,ametadata=print:key=lavfi.r128.M",
        "-f", "null", "-",
    ]
    # Momentary Loudness 변화 속도가 임계값 이상인 구간 → emotion_shift
    ...
```

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| Performance | 크로스페이드 인코딩 추가 시간 < 기존 대비 +20% |
| Performance | 스마트 키프레임 추출은 기존 균등 추출 대비 동일하거나 빠름 |
| Compatibility | 단일 클립(clips 없음) 하이라이트는 기존과 동일하게 동작 |
| Quality | 문장 중간 컷 발생률 기존 대비 80% 이상 감소 |
| Quality | 숏폼 첫 3초 시청 유지율 체감 개선 |

---

## 4. Architecture

### 4.1 변경 파일

| File | 변경 내용 | 개선 ID |
|------|-----------|---------|
| `services/highlight_analyzer.py` | `_snap_to_sentence_boundary()` 추가, `analyze_multimodal()`에 transcript 전달 | IMP-01 |
| `services/export_processor.py` | `_build_concat_with_crossfade_cmd()`, `_build_shortform_concat_with_crossfade_cmd()` 추가 | IMP-02 |
| `core/constants.py` | MULTIMODAL_SYSTEM_PROMPT에 Hook-first + Pacing 지시 추가 | IMP-03, IMP-05 |
| `core/config.py` | `crossfade_duration`, `snap_tolerance` 설정 추가 | IMP-01, IMP-02 |
| `services/keyframe_extractor.py` | `extract_smart()` 메서드 추가, `_extract_at_timestamps()` 내부 헬퍼 | IMP-04 |
| `services/video_processor.py` | 파이프라인 순서 변경 (오디오/장면 → 키프레임) | IMP-04 |
| `services/audio_analyzer.py` | `_extract_loudness_changes()` 추가, 핫스팟 타입 확장 | IMP-06 |

### 4.2 개선된 파이프라인 흐름

```
_analyze_video(video_id):
  Step 1: 오디오 추출 (기존)
  Step 2: STT (기존)
  Step 3: 오디오 에너지 + 라우드니스 분석 (IMP-06 확장)  ← 순서 변경
  Step 4: 장면 전환 감지 (기존)                          ← 순서 변경
  Step 5: 스마트 키프레임 추출 (IMP-04)                   ← 이벤트 시점 활용
  Step 6: GPT-4o 멀티모달 분석 (IMP-03, IMP-05 프롬프트)
  Step 7: 문장 경계 스냅 (IMP-01)                        ← NEW 후처리
  Step 8: DB 저장

  Export 시:
  Step 9: 크로스페이드 트랜지션 (IMP-02)                  ← concat 교체
```

### 4.3 크로스페이드 FFmpeg 필터 상세

```
클립 3개 (A, B, C), fade=0.3초:

입력: -ss A.start -t A.dur -i video
      -ss B.start -t B.dur -i video
      -ss C.start -t C.dur -i video

필터:
[0:v]setpts=PTS-STARTPTS[v0];
[1:v]setpts=PTS-STARTPTS[v1];
[2:v]setpts=PTS-STARTPTS[v2];
[0:a]asetpts=PTS-STARTPTS[a0];
[1:a]asetpts=PTS-STARTPTS[a1];
[2:a]asetpts=PTS-STARTPTS[a2];

[v0][v1]xfade=transition=fade:duration=0.3:offset={dA-0.3}[xv1];
[xv1][v2]xfade=transition=fade:duration=0.3:offset={dA+dB-0.6}[outv];

[a0][a1]acrossfade=d=0.3:c1=tri:c2=tri[xa1];
[xa1][a2]acrossfade=d=0.3:c1=tri:c2=tri[outa]

출력 길이 = dA + dB + dC - 0.6  (fade 2회분 감소)
```

### 4.4 config.py 추가 설정

| Setting | Default | Description |
|---------|---------|-------------|
| `crossfade_duration` | `0.3` | 클립 간 크로스페이드 길이 (초) |
| `snap_tolerance` | `2.0` | 문장 경계 스냅 허용 오차 (초) |

---

## 5. Implementation Order

구현 순서는 의존성과 효과/난이도 비율을 고려하여 설정한다.

```
Phase 1 (P0 — 즉시 체감):
  IMP-01: 문장 경계 스냅         → highlight_analyzer.py
  IMP-02: 크로스페이드 트랜지션   → export_processor.py, config.py
  IMP-03: 훅 퍼스트 프롬프트     → constants.py

Phase 2 (P1 — 분석 품질):
  IMP-04: 스마트 키프레임        → keyframe_extractor.py, video_processor.py
  IMP-05: 페이싱 프롬프트        → constants.py

Phase 3 (P2 — 고급 오디오):
  IMP-06: 오디오 감정 분류       → audio_analyzer.py
```

---

## 6. Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| xfade 필터 FFmpeg 버전 요구 | Medium | xfade는 FFmpeg 4.3+ 필요, 미지원 시 기존 concat 폴백 |
| 크로스페이드로 총 길이 감소 | Low | fade 횟수 x duration만큼 감소, 최소 길이 검증에 반영 |
| 문장 경계 스냅 후 클립 길이 변화 | Low | 스냅 후 3초 미만 클립 재검증 |
| 스마트 키프레임의 이벤트 과밀 | Low | 2초 간격 디디피 + max_count 상한 |
| 훅 퍼스트 재배열로 맥락 손실 | Medium | 프롬프트에 "임팩트 후 맥락 제공" 지시 |
| ebur128 필터 미지원 FFmpeg | Low | 라우드니스 분석 실패 시 기존 RMS만 사용 |

---

## 7. Success Criteria

- [ ] 서브클립 2개 이상 하이라이트에서 크로스페이드가 적용된 영상 출력
- [ ] 클립 start/end가 STT 세그먼트 경계 +-0.5초 이내에 위치 (80% 이상)
- [ ] 하이라이트 첫 클립이 score 기준 상위 순간인 비율 70% 이상
- [ ] 키프레임이 장면 전환 시점을 80% 이상 커버
- [ ] 단일 클립 하이라이트는 기존과 동일하게 동작 (하위 호환)
- [ ] xfade 미지원 FFmpeg에서 기존 concat으로 폴백 동작

---

## 8. Next Steps

1. [ ] Design 문서 작성 (`/pdca design highlight-quality`)
2. [ ] Phase 1 (P0) 구현: IMP-01, IMP-02, IMP-03
3. [ ] Phase 2 (P1) 구현: IMP-04, IMP-05
4. [ ] Phase 3 (P2) 구현: IMP-06
5. [ ] 실제 영상 A/B 테스트: 개선 전/후 비교

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-08 | Initial draft — 6가지 품질 개선 전체 계획 | Claude |
