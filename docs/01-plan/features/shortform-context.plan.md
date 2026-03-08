# shortform-context Planning Document

> **Summary**: 숏폼 다운로드 영상에 맥락 구간을 포함하여 원본 미시청자도 이해 가능한 30~55초 숏폼 생성
>
> **Project**: Shortify
> **Version**: 0.4.1
> **Date**: 2026-03-09
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 현재 숏폼은 핵심 순간만 추출 + Hook-first 재배열하여, 원본을 모르는 시청자가 맥락을 파악하기 어렵고 영상 길이도 지나치게 짧다 |
| **Solution** | (1) GPT 프롬프트에 맥락 셋업 클립 포함 지시 추가, (2) Export 시 각 클립 앞에 컨텍스트 패딩을 STT 문장 경계 기준으로 확장, 목표 길이 30~55초 |
| **Function/UX Effect** | 숏폼 시작 시 "이건 ~에 대한 이야기인데" 맥락이 나온 후 핵심이 나와 처음 보는 시청자도 내용을 이해할 수 있고, 적절한 길이로 시청 완주율 상승 |
| **Core Value** | "이해 가능한 숏폼" — 임팩트와 맥락의 균형으로 바이럴 가능한 독립적 숏폼 콘텐츠 생성 |

---

## 1. Overview

### 1.1 현재 문제

```
GPT가 뽑은 클립:  [핵심 8초]  [결론 6초]   = 13.7초 (패딩 후 15초)
시청자 경험:      "갑자기 뭔소리지?" → 스크롤

원본 구조:  [도입 설명]──[맥락]──[핵심!]──[부연]──[결론]
숏폼:                            [핵심!]         [결론]  ← 맥락 없음
```

### 1.2 목표

```
개선 숏폼:  [맥락 셋업 5초]──[핵심! 10초]~~fade~~[정리 5초]──[결론 8초]
            "오늘 주제는..."   "핵심은 이겁니다!"            "정리하면"

            총 길이: ~30~55초, 맥락 포함, 독립적으로 이해 가능
```

---

## 2. Scope

### 2.1 In Scope

| ID | 개선 | 변경 대상 | 우선순위 |
|----|------|-----------|----------|
| CTX-01 | GPT 프롬프트에 맥락 클립 포함 지시 | `constants.py` | P0 |
| CTX-02 | 컨텍스트 패딩 — 클립 앞에 STT 문장 경계 기준 확장 | `highlight_analyzer.py` | P0 |
| CTX-03 | 목표 길이 조절 — 하이라이트 총 길이 30~55초 목표 | `constants.py`, `highlight_analyzer.py` | P0 |
| CTX-04 | config에 패딩 설정 추가 | `config.py` | P0 |

### 2.2 Out of Scope

- 프론트엔드 클립 재생 방식 변경 (기존 start_time~end_time 연속 재생 유지)
- 자막/텍스트 오버레이 (별도 기능)
- 사용자가 맥락 길이를 UI에서 조절하는 기능

---

## 3. Requirements

### 3.1 Functional Requirements

#### CTX-01: GPT 프롬프트 맥락 지시

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | MULTIMODAL_SYSTEM_PROMPT에 "각 하이라이트는 맥락 셋업 클립을 포함해야 한다" 지시를 추가한다 | High |
| FR-02 | "처음 보는 시청자가 이 숏폼만으로 내용을 이해할 수 있어야 한다"는 원칙을 명시한다 | High |
| FR-03 | Hook-first 규칙을 수정: Hook 후 반드시 맥락 Context 클립이 와야 한다 | High |
| FR-04 | 목표 총 길이를 30~55초로 변경한다 (현재 15~60초) | Medium |

**프롬프트 추가 내용**:
```
- **Context-first comprehension**: Each highlight must be understandable
  WITHOUT watching the original video. Include a brief "setup" clip (3-5 seconds)
  that provides context BEFORE or AFTER the hook. The viewer should understand
  "what topic is being discussed" within the first 8 seconds.
  Structure: [Hook 2-3s] -> [Setup/Context 3-5s] -> [Key Content] -> [Wrap-up]
- Target total duration: 30-55 seconds per highlight. Shorter highlights
  lack context; aim for a complete mini-narrative.
```

#### CTX-02: 컨텍스트 패딩

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-05 | Export 시 각 클립의 start를 N초 앞으로 확장하여 맥락 구간을 포함한다 | High |
| FR-06 | 확장 시 가장 가까운 STT 세그먼트 시작점까지 확장하여 문장 시작부터 포함한다 | High |
| FR-07 | 기본 패딩은 3초, config에서 조절 가능하다 | Medium |
| FR-08 | 패딩 후 총 길이가 60초를 초과하면 패딩을 줄여서 조절한다 | High |
| FR-09 | 첫 번째 클립의 start가 0 미만이 되지 않도록 클램핑한다 | High |
| FR-10 | 패딩으로 인접 클립과 겹치면 겹침 구간을 제거한다 | Medium |

**구현 위치**: `highlight_analyzer.py` — `_parse_multimodal_response()` 후처리, 스냅 후 패딩 적용

**로직**:
```python
def _add_context_padding(self, clips, transcript, duration, padding=3.0):
    """각 클립 앞에 맥락 패딩 추가 (STT 세그먼트 경계 기준)"""
    seg_starts = [seg.start for seg in transcript.segments]

    padded = []
    for clip in clips:
        new_start = clip["start"] - padding
        new_start = max(0.0, new_start)

        # STT 세그먼트 시작점으로 스냅 (문장 시작부터 포함)
        if seg_starts:
            best = min(seg_starts, key=lambda b: abs(b - new_start))
            if best <= clip["start"] and abs(best - new_start) <= padding + 1:
                new_start = best

        padded.append({"start": new_start, "end": clip["end"]})

    # 인접 클립 겹침 제거
    for i in range(1, len(padded)):
        if padded[i]["start"] < padded[i-1]["end"]:
            padded[i]["start"] = padded[i-1]["end"]

    # 총 길이 60초 초과 시 패딩 축소
    total = sum(c["end"] - c["start"] for c in padded)
    if total > 60:
        # 패딩을 비례적으로 줄임
        ...

    return padded
```

#### CTX-03: 목표 길이 조절

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-11 | 하이라이트 총 길이 검증 범위를 15~60초에서 30~55초로 변경한다 | Medium |
| FR-12 | 총 길이가 30초 미만이면 클립을 확장하거나 패딩을 늘린다 | Medium |
| FR-13 | 총 길이가 55초 초과이면 패딩을 우선 축소한다 | Medium |

#### CTX-04: config 설정

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-14 | `context_padding` 설정 추가 (기본 3.0초) | Medium |
| FR-15 | `highlight_min_duration` 설정 추가 (기본 30초) | Medium |
| FR-16 | `highlight_max_duration` 설정 추가 (기본 55초) | Medium |

---

## 4. Architecture

### 4.1 변경 파일

| File | 변경 내용 |
|------|-----------|
| `core/config.py` | `context_padding`, `highlight_min_duration`, `highlight_max_duration` 추가 |
| `core/constants.py` | MULTIMODAL_SYSTEM_PROMPT에 맥락 포함 + 목표 길이 지시 추가 |
| `services/highlight_analyzer.py` | `_add_context_padding()` 추가, `_parse_multimodal_response()`에 패딩 후처리 |

### 4.2 처리 흐름

```
GPT-4o 응답
  ↓
클립 검증 (기존)
  ↓
문장 경계 스냅 (기존 IMP-01)
  ↓
컨텍스트 패딩 (NEW — CTX-02)     ← 각 클립 앞에 3초 맥락 추가
  ↓
총 길이 조절 (NEW — CTX-03)      ← 30~55초 범위로 조절
  ↓
DB 저장
  ↓
Export 시: 패딩 포함된 clips으로 xfade concat (기존 IMP-02)
```

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| 패딩으로 60초 초과 | Medium | 총 길이 초과 시 패딩 비례 축소 |
| 패딩으로 인접 클립 겹침 | Low | 겹침 구간 앞 클립 우선, 뒤 클립 start 조정 |
| GPT가 맥락 클립을 이미 포함하는 경우 이중 패딩 | Low | 패딩 후 최대 55초 상한으로 제어 |
| 영상 시작부 클립의 패딩이 0초 미만 | Low | `max(0.0, new_start)` 클램핑 |

---

## 6. Success Criteria

- [ ] 숏폼 첫 8초 내에 주제/맥락을 파악할 수 있는 내용이 포함됨
- [ ] 숏폼 평균 길이가 30~55초 범위
- [ ] 원본 미시청자가 숏폼만으로 내용을 이해할 수 있음
- [ ] 기존 단일 클립 하이라이트도 정상 동작 (하위 호환)
- [ ] 패딩으로 인한 클립 겹침이 없음

---

## 7. Next Steps

1. [ ] Design 문서 작성 (`/pdca design shortform-context`)
2. [ ] 구현: config → 프롬프트 → 패딩 로직 → 길이 조절
3. [ ] 실제 영상 테스트

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial draft | Claude |
