# PDCA Completion Report: multimodal-highlight

> **Feature**: 멀티모달 분석(키프레임+오디오+장면전환) + 서브클립 자동 편집
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
| **Design Match Rate** | 100% (13/13 PASS) |
| **Iterations Required** | 1 (3 gaps found, fixed, re-verified) |
| **New Files Created** | 3 |
| **Files Modified** | 10 |
| **New Dependencies** | 0 (FFmpeg + OpenAI API only) |

### 1.2 Project Overview

| Item | Value |
|------|-------|
| Feature | multimodal-highlight |
| Started | 2026-03-08 |
| Completed | 2026-03-08 |
| PDCA Phases | Plan -> Design -> Do -> Check (77%) -> Fix -> Re-check (100%) -> Report |

### 1.3 Value Delivered

| Perspective | Result |
|-------------|--------|
| **Problem** | 기존 하이라이트는 텍스트만 분석하여 시각/오디오 신호를 놓치고, 연속 구간만 잘라내서 불필요한 장면이 포함되었음 |
| **Solution** | 키프레임(10초 간격) + 오디오 에너지(astats RMS) + 장면 전환(scene detect) 3가지 신호를 GPT-4o 멀티모달 API에 함께 전달. 하이라이트를 서브클립 배열로 반환받아 FFmpeg concat으로 편집 Export |
| **Function/UX Effect** | 비주얼/오디오 하이라이트까지 감지되고, 불필요한 구간은 자동 제거됨. Frontend에 "N개 클립 편집 (MM:SS)" 표시. 기존 단일 구간 하이라이트도 100% 하위 호환 |
| **Core Value** | "AI 자동 편집" — 단순 클리핑을 넘어 영상의 핵심만 이어붙인 프로급 숏폼 자동 생성. 추가 라이브러리 없이 FFmpeg + OpenAI만으로 구현 |

---

## 2. PDCA Cycle Summary

### 2.1 Plan Phase

**Document**: `docs/01-plan/features/multimodal-highlight.plan.md`

- 13개 기능 요구사항 정의 (FR-01 ~ FR-13)
- 3레벨 통합: 키프레임(L1) + 오디오 에너지(L2) + 장면 전환(L3)
- 서브클립 자동 편집 (접근 A: AI 자동 구성)
- 비용 최적화 전략: `detail: "low"` + 512px 리사이즈 + max 30프레임

### 2.2 Design Phase

**Document**: `docs/02-design/features/multimodal-highlight.design.md`

- 새 파일 3개 + 변경 파일 10개 = 총 13개 파일 설계
- GPT-4o 멀티모달 메시지 구조 상세 설계
- 서브클립 DB 모델 (clips JSON 컬럼)
- Export 4가지 분기 (단일/다중 x 원본/숏폼)
- 13개 Verification Items 정의

### 2.3 Do Phase

**Created Files** (3):

| # | File | Description |
|---|------|-------------|
| 1 | `services/keyframe_extractor.py` | FFmpeg 키프레임 JPEG 추출 + base64 인코딩 + 임시 파일 정리 |
| 2 | `services/audio_analyzer.py` | FFmpeg astats RMS 에너지 분석 + 볼륨 급상승/무음 전환 핫스팟 |
| 3 | `services/scene_detector.py` | FFmpeg scene detect 장면 전환 타임스탬프 |

**Modified Files** (10):

| # | File | Change |
|---|------|--------|
| 4 | `core/config.py` | `gpt-4o` 모델 + keyframe/scene/audio 설정 6개 |
| 5 | `core/constants.py` | `MULTIMODAL_SYSTEM_PROMPT` + `MULTIMODAL_USER_PROMPT` |
| 6 | `services/highlight_analyzer.py` | `analyze_multimodal()` + clips 파싱 + HighlightResult.clips |
| 7 | `infrastructure/models.py` | Highlight에 `clips` JSON 컬럼 |
| 8 | `models/schemas.py` | `ClipSegment` + HighlightBase.clips |
| 9 | `infrastructure/repository.py` | create_batch + video_to_dict에 clips |
| 10 | `services/video_processor.py` | 파이프라인 Step 3~5 + fallback |
| 11 | `services/export_processor.py` | `_build_concat_cmd` + `_build_shortform_concat_cmd` + clips 필드 |
| 12 | `api/highlights.py` | clips 반환 + export 시 clips 전달 |
| 13 | Frontend (4 files) | types/api.ts/HighlightCard/page.tsx clips 지원 |

### 2.4 Check Phase

**Document**: `docs/03-analysis/multimodal-highlight.analysis.md`

- 1차 분석: **77%** (10/13) — 3개 Gap 발견
- Gap 수정 후 재분석: **100%** (13/13)

| Gap | 수정 내용 |
|-----|----------|
| `video_to_dict` clips 누락 | `repository.py:180` 추가 |
| `get_highlight` clips 누락 | `highlights.py:41` 추가 |
| `_build_shortform_concat_cmd` 미구현 | `export_processor.py:349-406` 추가 |

---

## 3. Technical Architecture

### 3.1 분석 파이프라인

```
영상 업로드
  -> Step 1: FFmpeg 오디오 추출 (WAV 16kHz mono)
  -> Step 2: Whisper STT (텍스트 + 타임스탬프)
  -> Step 3: FFmpeg 키프레임 추출 (10초 간격, 512px JPEG)
  -> Step 4: FFmpeg astats 오디오 에너지 (RMS dB per second)
  -> Step 5: FFmpeg scene detect (장면 전환 시점)
  -> Step 6: GPT-4o 멀티모달 분석
       입력: 텍스트 + 키프레임 이미지(base64) + 오디오 핫스팟 + 장면 전환
       출력: clips 배열 하이라이트 [{clips: [{start, end}, ...]}, ...]
  -> Step 7: DB 저장 (clips JSON 포함)
```

### 3.2 Export 분기 매트릭스

| clips | layout | 메서드 |
|:-----:|:------:|--------|
| 없음 | original | 기존 `-ss -t` 클리핑 |
| 없음 | shortform | `_build_shortform_cmd` (9:16 + 블러) |
| 다중 | original | `_build_concat_cmd` (trim + concat) |
| 다중 | shortform | `_build_shortform_concat_cmd` (concat + 9:16) |

### 3.3 비용 추정 (5분 영상)

| 항목 | 토큰/비용 |
|------|----------|
| Whisper STT | ~$0.03 |
| GPT-4o 텍스트 | ~$0.02 |
| GPT-4o 이미지 (30프레임 x 85토큰) | ~$0.01 |
| **총 추가 비용** | **~$0.06** |

---

## 4. Verification Results

| ID | Verification | Result |
|----|-------------|:------:|
| V-01 | FFmpeg 키프레임 JPEG + base64 | PASS |
| V-02 | max_count 초과 시 interval 조절 | PASS |
| V-03 | FFmpeg astats RMS 에너지 | PASS |
| V-04 | 볼륨 급상승 핫스팟 | PASS |
| V-05 | FFmpeg scene detect | PASS |
| V-06 | 멀티모달 메시지 구성 | PASS |
| V-07 | clips 배열 JSON 파싱 | PASS |
| V-08 | DB clips JSON 컬럼 | PASS |
| V-09 | 단일 클립 기존 방식 | PASS |
| V-10 | 다중 클립 concat | PASS |
| V-11 | 다중 클립 + shortform | PASS |
| V-12 | Frontend clips 표시 | PASS |
| V-13 | Fallback 텍스트 분석 | PASS |

---

## 5. PDCA Documents

| Phase | Document |
|-------|----------|
| Plan | `docs/01-plan/features/multimodal-highlight.plan.md` |
| Design | `docs/02-design/features/multimodal-highlight.design.md` |
| Analysis | `docs/03-analysis/multimodal-highlight.analysis.md` |
| Report | `docs/04-report/multimodal-highlight.report.md` |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-03-08 | Completion report | Claude |
