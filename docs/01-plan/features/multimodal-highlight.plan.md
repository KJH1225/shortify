# multimodal-highlight Planning Document

> **Summary**: 멀티모달 분석(텍스트+키프레임+오디오+장면전환) + 서브클립 자동 편집으로 하이라이트 품질 대폭 개선
>
> **Project**: Shortify
> **Version**: 0.3.0
> **Date**: 2026-03-08
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 현재 하이라이트는 텍스트만 분석하여 시각/오디오 신호를 놓치고, 연속 구간만 잘라내서 불필요한 장면이 포함되거나 흩어진 명장면을 합칠 수 없다 |
| **Solution** | 키프레임+오디오 에너지+장면 전환을 GPT-4o에 함께 전달하고, 하이라이트를 서브클립 배열(clips)로 반환받아 FFmpeg concat으로 짜집기한다 |
| **Function/UX Effect** | 비주얼/오디오 하이라이트까지 감지되고, 불필요한 구간은 자동 제거되어 편집된 숏폼이 바로 Export된다 |
| **Core Value** | "AI 자동 편집" — 단순 클리핑을 넘어 영상의 핵심만 이어붙인 프로급 숏폼 자동 생성 |

---

## 1. Overview

### 1.1 Purpose

현재 파이프라인:
```
영상 → 오디오 추출 → Whisper STT → 텍스트만 GPT-4o-mini → 하이라이트
```

개선 파이프라인:
```
영상 ─┬─ 오디오 추출 → Whisper STT → 텍스트 ─────┐
      ├─ 키프레임 캡처 (10초 간격) → 이미지들 ──────┤
      ├─ 오디오 에너지 분석 → 핫스팟 ──────────────┤→ GPT-4o → 서브클립 배열
      └─ 장면 전환 감지 → scene changes ───────────┘    [{start,end}, ...]
                                                          ↓
                                                    FFmpeg concat → 편집된 숏폼
```

### 1.2 Background

- GPT-4o는 텍스트+이미지를 동시에 이해하는 멀티모달 모델
- 현재 `openai_chat_model = "gpt-4o-mini"` → `"gpt-4o"`로 변경하면 이미지 입력 지원
- FFmpeg `fps=1/10` 필터로 10초 간격 프레임 추출 가능 (5분 영상 = 30프레임)
- FFmpeg `astats` 필터로 구간별 오디오 에너지(RMS level) 추출 가능
- 추가 라이브러리 불필요 — FFmpeg + OpenAI API만으로 구현

---

## 2. Scope

### 2.1 In Scope

- [x] FFmpeg 키프레임 추출 서비스 (`keyframe_extractor.py`)
- [x] FFmpeg 오디오 에너지 분석 서비스 (`audio_analyzer.py`)
- [x] GPT-4o 멀티모달 프롬프트 (텍스트 + 이미지 + 오디오 핫스팟)
- [x] `highlight_analyzer.py` 멀티모달 분석 메서드
- [x] `video_processor.py` 파이프라인에 새 단계 삽입
- [x] 설정: 키프레임 간격, 이미지 크기, 모델명 설정 가능
- [x] 비용 최적화: 이미지 리사이즈 (512px 이하), 프레임 수 제한
- [x] FFmpeg 장면 전환 감지 (`select='gt(scene,0.3)'`)
- [x] 하이라이트를 서브클립 배열(`clips`)로 반환받는 GPT 프롬프트
- [x] Highlight DB 모델에 `clips` JSON 컬럼 추가
- [x] FFmpeg concat 필터로 서브클립 이어붙이기 Export
- [x] Frontend: 서브클립 정보 표시 (총 길이, 클립 수)

### 2.2 Out of Scope

- 사용자 수동 타임라인 편집 UI (향후 확장)
- 로컬 비전 모델 (CLIP, BLIP 등) — API 기반으로 충분
- 실시간 영상 스트림 분석
- GPU 의존 기능
- 클립 간 트랜지션 효과 (컷 편집만)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | FFmpeg으로 영상에서 N초 간격 키프레임을 JPEG 추출한다 | High | Pending |
| FR-02 | 키프레임 이미지를 512px 이하로 리사이즈한다 (비용 최적화) | High | Pending |
| FR-03 | FFmpeg astats로 1초 단위 오디오 RMS 에너지를 추출한다 | Medium | Pending |
| FR-04 | 오디오 에너지 상위 구간을 핫스팟으로 식별한다 | Medium | Pending |
| FR-05 | GPT-4o 멀티모달 API에 텍스트+이미지+오디오 핫스팟을 함께 전달한다 | High | Pending |
| FR-06 | 시스템 프롬프트를 멀티모달 분석에 맞게 강화한다 | High | Pending |
| FR-07 | 기존 텍스트 전용 분석 모드를 fallback으로 유지한다 (API 키 또는 모델 미지원 시) | Medium | Pending |
| FR-08 | config에 keyframe_interval, keyframe_max_count, keyframe_width 설정 추가 | Medium | Pending |
| FR-09 | FFmpeg scene detect 필터로 장면 전환 타임스탬프를 추출한다 | Medium | Pending |
| FR-10 | GPT에게 하이라이트를 `clips: [{start, end}, ...]` 서브클립 배열로 반환하도록 한다 | High | Pending |
| FR-11 | Highlight DB 모델에 `clips` JSON 컬럼을 추가한다 (기존 start_time/end_time은 첫 클립~마지막 클립 범위) | High | Pending |
| FR-12 | Export 시 서브클립이 있으면 FFmpeg concat 필터로 이어붙인다 | High | Pending |
| FR-13 | Frontend에서 서브클립 수와 총 편집 길이를 표시한다 | Medium | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| Performance | 키프레임 추출 5분 영상 기준 5초 이내 |
| Cost | 5분 영상 30프레임 기준 추가 비용 ~$0.10 이내 |
| Quality | 시각 전용 하이라이트(말 없는 장면) 1개 이상 추출 |

---

## 4. Architecture

### 4.1 새 파일

| File | 역할 |
|------|------|
| `services/keyframe_extractor.py` | FFmpeg 키프레임 JPEG 추출 + 리사이즈 |
| `services/audio_analyzer.py` | FFmpeg astats 오디오 에너지 분석 + 핫스팟 추출 |
| `services/scene_detector.py` | FFmpeg scene detect 장면 전환 감지 |

### 4.2 변경 파일

| File | 변경 |
|------|------|
| `core/config.py` | keyframe/audio/scene 분석 설정 추가 |
| `core/constants.py` | 멀티모달+서브클립 시스템 프롬프트 추가 |
| `services/highlight_analyzer.py` | `analyze_multimodal()` 서브클립 배열 반환 |
| `services/video_processor.py` | 파이프라인에 키프레임+오디오+장면전환 단계 삽입 |
| `services/export_processor.py` | 서브클립 concat Export 지원 |
| `infrastructure/models.py` | Highlight에 `clips` JSON 컬럼 추가 |
| `models/schemas.py` | HighlightResponse에 `clips` 필드 추가 |
| `infrastructure/repository.py` | clips 저장/조회 처리 |
| `frontend/src/types/index.ts` | Highlight에 clips 타입 추가 |
| `frontend/src/components/molecules/HighlightCard.tsx` | 서브클립 정보 표시 |

### 4.3 데이터 흐름 상세

```
_analyze_video(video_id):
  Step 1: 오디오 추출 (기존, 10-20%)
  Step 2: STT (기존, 20-50%)
  Step 3: 키프레임 추출 (NEW, 50-55%)
    → FFmpeg -vf "fps=1/{interval},scale={width}:-1" → JPEG 파일들
    → base64 인코딩 → images: list[str]
  Step 4: 오디오 에너지 분석 (NEW, 55-58%)
    → FFmpeg astats → 1초 단위 RMS 값들
    → 상위 N개 핫스팟 추출 → hotspots: list[AudioHotspot]
  Step 5: 장면 전환 감지 (NEW, 58-60%)
    → FFmpeg select='gt(scene,0.3)' → scene_changes: list[float]
  Step 6: 멀티모달 하이라이트 분석 (기존 강화, 60-90%)
    → GPT-4o: 텍스트 + 키프레임 + 오디오 핫스팟 + 장면 전환
    → 서브클립 배열로 하이라이트 반환
  Step 7: DB 저장 (기존, 90-100%) — clips JSON 포함
```

### 4.4 GPT-4o 멀티모달 메시지 구조

```python
messages = [
    {"role": "system", "content": MULTIMODAL_SYSTEM_PROMPT},
    {"role": "user", "content": [
        {"type": "text", "text": f"""
Video duration: {duration}s
Target: {target_count} highlights

=== Transcript ===
{transcript_text}

=== Audio Hotspots ===
{hotspot_text}
        """},
        # 키프레임 이미지들 (10초 간격)
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_0}", "detail": "low"}},
        {"type": "text", "text": "[Frame at 00:00]"},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_10}", "detail": "low"}},
        {"type": "text", "text": "[Frame at 00:10]"},
        # ...
    ]},
]
```

`detail: "low"` → 고정 85 토큰/이미지, 30프레임 = 2,550 토큰 추가 ($0.008)

---

## 5. Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| GPT-4o 비용 증가 | Medium | `detail: "low"` + 프레임 수 제한(최대 30) + 이미지 512px 리사이즈 |
| 긴 영상에서 프레임 수 폭발 | Medium | `keyframe_max_count` 상한 설정 (기본 30) |
| GPT-4o 토큰 한도 초과 | Low | 이미지 수 동적 조절, 트랜스크립트 요약 |
| 오디오 분석 실패 (무음 영상) | Low | 오디오 핫스팟 0개면 텍스트+이미지만 전달 |

---

## 6. Success Criteria

- [ ] 시각 전용 하이라이트(말 없는 장면)가 추출 결과에 포함됨
- [ ] 오디오 에너지 핫스팟이 프롬프트에 반영됨
- [ ] 장면 전환 정보가 프롬프트에 반영됨
- [ ] 하이라이트가 서브클립 배열(clips)로 반환됨
- [ ] Export 시 서브클립이 concat되어 편집된 영상 출력
- [ ] 기존 단일 구간 하이라이트도 정상 동작 (하위 호환)
- [ ] 5분 영상 기준 전체 분석 시간 2분 이내

---

## 7. Next Steps

1. [ ] Design 문서 작성
2. [ ] 구현 및 테스트
3. [ ] 실제 영상으로 품질 비교 (텍스트 전용 vs 멀티모달)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-08 | Initial draft | Claude |
