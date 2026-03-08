# shortform-layout Planning Document

> **Summary**: 숏폼 Export 영상의 9:16 캔버스 레이아웃 + 세이프존 적용
>
> **Project**: Shortify
> **Version**: 0.2.0
> **Date**: 2026-03-08
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 현재 Export는 원본 비율 그대로 클리핑만 하므로, 가로/정방형 영상이 숏폼 플랫폼에서 작게 표시되고 플랫폼 UI에 콘텐츠가 가려진다. 반면 원본 비율이 필요한 경우도 있다 |
| **Solution** | Export 시 "원본 유지" / "숏폼(9:16)" 레이아웃을 선택할 수 있도록 하고, 숏폼 선택 시 FFmpeg 필터 체인으로 세이프존 적용 + 블러 배경 처리 |
| **Function/UX Effect** | HighlightCard에서 Export 버튼 클릭 시 레이아웃을 선택할 수 있고, 숏폼 모드는 별도 편집 없이 바로 업로드 가능한 영상을 생성한다 |
| **Core Value** | "추출에서 업로드까지 원스톱" — 용도에 따라 원본/숏폼을 선택하여 하이라이트를 바로 활용 가능 |

---

## 1. Overview

### 1.1 Purpose

현재 Export 파이프라인(`export_processor.py:155-167`)은 원본 영상을 시간 구간만 잘라내는 단순 클리핑만 수행한다. 원본이 16:9 가로 영상이면 Export 결과도 16:9이므로, 숏폼 플랫폼에 업로드하면 화면의 절반만 차지하고 나머지는 검은 여백이 된다.

이 기능은 Export 시 **두 가지 레이아웃 옵션**을 제공한다:
1. **원본 유지** — 기존과 동일하게 원본 비율 그대로 클리핑 (기본값)
2. **숏폼(9:16)** — 9:16 세로 캔버스에 세이프존 적용 + 블러 배경

### 1.2 Background

- 숏폼 플랫폼(TikTok, Instagram Reels, YouTube Shorts)은 모두 **9:16(1080x1920)** 세로 영상을 기본으로 한다
- 하단 ~35%에는 캡션/댓글/좋아요 UI가 겹치고, 상단 ~15%에는 프로필/팔로우 UI가 겹친다
- 현재 Shortify 사용자가 Export 후 별도 편집 앱(CapCut 등)에서 비율 변환을 해야 하는 불편이 있다
- 단, 원본 비율이 필요한 경우(편집 소스, 아카이브 등)도 있으므로 **선택형**이 적합하다
- 서버 사이드 FFmpeg 필터로 자동 처리하면 사용자 워크플로우가 크게 단축된다

### 1.3 Related Documents

- Existing: `docs/02-design/features/highlight-download.design.md`
- Existing: `backend/src/services/export_processor.py`

---

## 2. Scope

### 2.1 In Scope

- [x] Export 시 레이아웃 선택 옵션: "original" (원본 유지) / "shortform" (9:16)
- [x] 숏폼 모드: 9:16 캔버스(1080x1920) 고정 출력
- [x] 숏폼 모드: 가로(16:9) 영상 → 세이프존 내 중앙 배치 + 블러 배경
- [x] 숏폼 모드: 정방형(1:1) 영상 → 세이프존 내 중앙 배치 + 블러 배경
- [x] 숏폼 모드: 세로(9:16) 영상 → 리사이즈만 수행
- [x] 세이프존: 상단 15%(288px) / 하단 35%(672px) 비우기 → 콘텐츠 영역 960px
- [x] Backend: Export API에 `layout` 파라미터 추가 (기본값: `original`)
- [x] Frontend: HighlightCard Export 버튼에 레이아웃 선택 UI
- [x] FFmpeg 필터 체인으로 서버 사이드 처리
- [x] 기존 Export 동작 하위 호환 (`layout` 미지정 시 `original`)

### 2.2 Out of Scope

- 사용자 커스텀 비율 선택 (향후 확장)
- 자막/텍스트 오버레이
- 프론트엔드 실시간 프리뷰 (이번 스코프 외)
- 세이프존 비율 사용자 조정 UI

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | Export API에 `layout` 파라미터를 추가한다 (`"original"` / `"shortform"`, 기본값 `"original"`) | High | Pending |
| FR-02 | `layout=original`: 기존과 동일하게 원본 비율 클리핑 (하위 호환) | High | Pending |
| FR-03 | `layout=shortform`: 출력 해상도를 1080x1920(9:16)으로 고정한다 | High | Pending |
| FR-04 | 숏폼 모드에서 원본 비율을 감지하여 landscape/square/portrait로 분류한다 | High | Pending |
| FR-05 | 숏폼 모드에서 landscape/square 영상은 세이프존(상단 288px~하단 1248px, 960px 높이) 안에 fit한다 | High | Pending |
| FR-06 | 숏폼 모드에서 세이프존 밖 영역은 블러 배경으로 채운다 | High | Pending |
| FR-07 | 숏폼 모드에서 portrait 영상은 1080x1920으로 리사이즈만 수행한다 | Medium | Pending |
| FR-08 | 블러 배경은 원본 영상을 확대+가우시안 블러 처리하여 생성한다 | Medium | Pending |
| FR-09 | Frontend HighlightCard에 레이아웃 선택 UI를 추가한다 (원본/숏폼 토글) | High | Pending |
| FR-10 | `highlightApi.export()`에 `layout` 파라미터를 전달한다 | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 30초 클립 인코딩 15초 이내 (M1 Mac 기준) | FFmpeg 실행 시간 측정 |
| Quality | 출력 영상 최소 720p 품질, CRF 23 이하 | FFmpeg 인코딩 파라미터 |
| Compatibility | H.264/AAC MP4 — 모든 숏폼 플랫폼 호환 | 플랫폼 업로드 테스트 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] layout=original: 기존과 동일한 원본 비율 출력 확인
- [ ] layout=shortform + 가로(16:9) → 1080x1920, 세이프존 내 배치 확인
- [ ] layout=shortform + 정방형(1:1) → 1080x1920, 세이프존 내 배치 확인
- [ ] layout=shortform + 세로(9:16) → 1080x1920, 전체 화면 사용 확인
- [ ] 블러 배경이 여백 영역에 적용됨 확인
- [ ] Frontend에서 원본/숏폼 선택 후 Export 동작 확인
- [ ] layout 미지정 시 original로 동작 (하위 호환)

### 4.2 Quality Criteria

- [ ] FFmpeg 필터 체인 에러 없이 동작
- [ ] 출력 파일이 유효한 MP4
- [ ] 오디오 싱크 유지

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| FFmpeg 복합 필터 체인으로 인코딩 시간 증가 | Medium | High | preset=fast 유지, 필요시 GPU 가속 옵션 추가 |
| 극단적 비율 영상(21:9 등)에서 콘텐츠가 너무 작아짐 | Low | Low | 세이프존 내 최대 너비 1080px로 제한하되 최소 높이 보장 |
| 블러 배경 생성 시 메모리 사용량 증가 | Medium | Medium | scale 다운 후 블러 적용으로 메모리 최적화 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Selected |
|-------|-----------------|:--------:|
| **Dynamic** | Feature-based modules, Turborepo monorepo | ✅ |

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| 레이아웃 선택 방식 | API 파라미터 / 별도 엔드포인트 / 설정 기반 | **API 파라미터** | 기존 엔드포인트 유지 + body에 `layout` 필드 추가가 가장 단순 |
| 레이아웃 처리 위치 | Frontend(canvas) / Backend(FFmpeg) | **Backend(FFmpeg)** | 서버 사이드에서 확실한 품질 보장, 클라이언트 부하 없음 |
| 배경 처리 방식 | 단색(black) / 블러 배경 / 그라데이션 | **블러 배경** | 시각적으로 가장 자연스럽고 프로페셔널한 결과 |
| 비율 감지 방법 | ffprobe / 업로드 시 메타데이터 / 영상 헤더 파싱 | **ffprobe** | 가장 정확하고 모든 포맷 지원 |
| Frontend 선택 UI | 드롭다운 / 토글 버튼 / 모달 | **토글 버튼 그룹** | Export 전 빠르게 선택 가능, 최소한의 UI 변경 |
| 기본값 | original / shortform | **original** | 기존 동작 하위 호환 보장 |

### 6.3 Export 흐름 (레이아웃 선택 포함)

```
[Frontend]                              [Backend]
HighlightCard                           POST /api/highlights/{id}/export
  │                                       │
  ├─ 사용자: "원본" or "숏폼" 선택         ├─ body: { layout: "original" | "shortform" }
  │                                       │
  └─ highlightApi.export(id, layout) ──→  ├─ layout == "original"?
                                          │   └─ 기존 FFmpeg 클리핑 (변경 없음)
                                          │
                                          └─ layout == "shortform"?
                                              └─ 9:16 필터 체인 실행
```

### 6.4 FFmpeg 필터 체인 구조 (숏폼 모드)

```
원본 영상 입력 (layout=shortform)
    │
    ├─[1] ffprobe로 원본 width/height 조회
    │
    ├─[2] 비율 판정: landscape (w>h) / square (w==h) / portrait (w<h)
    │
    ├─[3] 캔버스: 1080x1920 (9:16)
    │     세이프존: y=288 ~ y=1248 (960px 높이)
    │     콘텐츠 영역: 1080 x 960
    │
    ├─[4] landscape/square인 경우:
    │     ┌─ 배경 레이어: 원본 → scale=1080:1920 → boxblur=20:20
    │     ├─ 콘텐츠 레이어: 원본 → scale=fit(1080x960) → overlay(center, y=288+offset)
    │     └─ 합성: 배경 위에 콘텐츠 overlay
    │
    └─[5] portrait인 경우:
          └─ 원본 → scale=1080:1920 → 출력
```

---

## 7. Convention Prerequisites

### 7.1 Existing Project Conventions

- [x] Atomic Design 컴포넌트 구조 (atoms/molecules/organisms/templates)
- [x] Repository Pattern (backend)
- [x] Pydantic Schema Validation
- [x] FFmpeg subprocess 호출 패턴 (`export_processor.py`, `audio_extractor.py`)

### 7.2 Conventions to Follow

| Category | Rule |
|----------|------|
| FFmpeg 호출 | `asyncio.create_subprocess_exec` 사용 (기존 패턴 유지) |
| 상수 관리 | `core/constants.py`에 캔버스/세이프존 값 정의 |
| 에러 처리 | ExportStatus.ERROR + error_message 패턴 유지 |

---

## 8. Next Steps

1. [ ] Design 문서 작성 (`shortform-layout.design.md`)
2. [ ] FFmpeg 필터 체인 프로토타이핑
3. [ ] 구현 및 검증

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-08 | Initial draft | Claude |
