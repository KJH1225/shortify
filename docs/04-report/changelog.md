# Shortify Changelog

## [2026-03-09] - Shortform Title Overlay Feature

### Added

- **Shortform Title Overlay**: FFmpeg drawtext 필터로 숏폼 내보내기 시 하이라이트 제목 자동 오버레이
  - 1080×1920px 영상 상단(y=130px)에 흰색 52px 텍스트 표시
  - 검정 테두리(3px)와 그림자 효과로 가독성 확보
  - 특수문자 FFmpeg 이스케이프 처리 완벽
  - 폰트 미존재 시 graceful fallback 지원

### Technical Details

**Modified Files**:
1. `backend/src/core/constants.py` - 8개 오버레이 상수 추가
2. `backend/src/services/export_processor.py` - ExportJob title 필드 + drawtext 필터 메서드 + shortform 메서드 통합
3. `backend/src/api/highlights.py` - highlight.title 전달

**Verification**: 100% gap analysis match rate (15/15 items verified), 0 iterations needed

### Quality Metrics

- Design Match Rate: **100%**
- Lines Added: 35줄
- Files Changed: 3개
- Implementation Time: 1일
- Issues Found: 0개

### Value Delivered

| 관점 | 내용 |
|------|------|
| **Problem** | 숏폼 내보내기 영상에 제목이 표시되지 않아 SNS 업로드 시 편집 필요 |
| **Solution** | FFmpeg drawtext로 DB 제목 자동 오버레이 |
| **Function/UX** | 영상 상단에 흰색 제목 텍스트 선명하게 표시 |
| **Core Value** | 별도 편집 없이 바로 사용 가능한 완성도 높은 숏폼 콘텐츠 생성 |

---

## [2026-02-08] - Critical Bug Fixes

### Fixed

- **Bug 1: POST Endpoint Data Loss** - Added explicit `await db.commit()` to `upload_video` and `process_youtube` endpoints to ensure video metadata persists before HTTP response
- **Bug 2: Highlight Data Rollback** - Eliminated nested sessions in `video_processor.py` by restructuring `_simulate_analysis()` into 3 independent session phases (progress → highlight insertion → status update)
- **Import Errors** - Fixed incorrect import paths in `export_processor.py` and `highlights.py` (changed `from core.config import settings` to `from core.config import get_settings`)

### Security

- Improved transaction safety by preventing nested session operations that could cause data loss
- Added `session.in_transaction()` safety check in `get_db()` to prevent double-commit scenarios

### Performance

- No performance degradation - each phase now operates in isolated, optimized transactions

### Technical Details

**Modified Files**:
1. `backend/src/infrastructure/database.py` - Added transaction state check
2. `backend/src/api/videos.py` - Added explicit commits in 2 endpoints
3. `backend/src/services/video_processor.py` - Restructured session management
4. `backend/src/services/export_processor.py` - Fixed import
5. `backend/src/api/highlights.py` - Fixed import

**Verification**: 100% gap analysis match rate (19/19 items verified)

---

## [2026-01-20] - Initial Project Completion (Previous PDCA Cycle)

### Added

- Complete Shortify service with AI video highlight extraction
- Full PDCA cycle completion (Plan → Design → Do → Check → Act)
- 99% design-implementation match rate achieved after 5 iterations

### Features

- Video upload and YouTube URL processing
- AI-powered highlight extraction (mock implementation)
- Export to short-form content using FFmpeg
- Real-time video processing status
- Complete API specification with 11 endpoints
- Data model with Video and Highlight entities
- Frontend UI with Next.js 15 and Tailwind CSS
- Backend API with FastAPI and SQLAlchemy 2.0

### Security

- XSS prevention with next/image and domain whitelist
- Input validation for files (extension, MIME type, size)
- URL validation for YouTube links (5 regex patterns)
- Rate limiting (60 requests / 60 seconds per IP)
- CORS configuration for localhost:3000

### Documentation

- API specification document
- Data model entity relationship diagram
- Complete PDCA project report with metrics
- Deployment guide and environment variable documentation

**Verification**: 99% design-implementation match rate (71/72 items verified)
