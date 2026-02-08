# Shortify

AI 기반 영상 하이라이트 자동 추출 및 숏폼 변환 서비스

> **Version**: 0.2.0
> **Match Rate**: 100% (PDCA 완료)

## 주요 기능

| 기능 | 설명 | 상태 |
|------|------|:----:|
| Video Upload | 영상 파일 업로드 + 검증 | ✅ |
| YouTube Processing | YouTube URL 영상 처리 | ✅ |
| AI Highlight Extraction | OpenAI Whisper + GPT 기반 하이라이트 자동 추출 | ✅ |
| Video Player | HTTP Range Request 스트리밍 + 하이라이트 타임라인 | ✅ |
| Video History | 과거 분석 영상 목록 조회, 재열기, 삭제 | ✅ |
| Export to Short-form | FFmpeg 기반 영상 클리핑 | ✅ |
| Real-time Status | 처리 상태 실시간 조회 | ✅ |

## 기술 스택

### Frontend
- **Next.js 15** (App Router)
- **TypeScript**
- **Tailwind CSS v4**
- **shadcn/ui** (UI 컴포넌트)
- **Zustand** (상태관리)

### Backend
- **FastAPI** (Python 3.13+)
- **SQLAlchemy 2.0** (Async ORM)
- **MySQL / SQLite**
- **Alembic** (DB Migration)
- **FFmpeg** (영상 처리)

### Infrastructure
- **Turborepo** (모노레포)
- **pnpm** (패키지 매니저)

## 시작하기

### 사전 요구사항

- Node.js 20+
- Python 3.13+
- pnpm
- FFmpeg
- MySQL 8.0+ (또는 SQLite for development)

### FFmpeg 설치

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

### 설치

```bash
# 1. 의존성 설치
pnpm install

# 2. Backend Python 가상환경 및 의존성 설치
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 환경 변수 설정

**Frontend** (`frontend/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Backend** (`backend/.env`):
```env
DATABASE_URL=sqlite+aiosqlite:///./shortify.db
# Production: mysql+aiomysql://user:pass@localhost:3306/shortify
OPENAI_API_KEY=your-openai-api-key
UPLOAD_DIR=./uploads
```

### 데이터베이스 마이그레이션

```bash
cd backend
source venv/bin/activate

# 마이그레이션 실행
alembic upgrade head
```

### 개발 서버 실행

```bash
# 전체 실행 (Frontend + Backend)
pnpm dev

# 개별 실행
pnpm dev:frontend  # Frontend (port 3000)
pnpm dev:backend   # Backend (port 8000)
```

또는 개별 터미널에서:

```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn src.main:app --reload

# Terminal 2 - Frontend
cd frontend
pnpm dev
```

### 접속

| 서비스 | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

## API 엔드포인트

### Videos API
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/videos/upload` | 영상 파일 업로드 |
| POST | `/api/videos/youtube` | YouTube URL 처리 |
| GET | `/api/videos/{id}` | 영상 정보 조회 |
| GET | `/api/videos/` | 영상 목록 조회 |
| GET | `/api/videos/{id}/stream` | 영상 스트리밍 (Range Request) |
| DELETE | `/api/videos/{id}` | 영상 삭제 |

### Highlights API
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/highlights/{id}` | 하이라이트 조회 |
| POST | `/api/highlights/{id}/export` | 숏폼 내보내기 |
| GET | `/api/highlights/{id}/export/{export_id}/status` | Export 상태 조회 |
| DELETE | `/api/highlights/{id}` | 하이라이트 삭제 |

### Health API
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/health` | 서버 상태 확인 |

## 프로젝트 구조

```
shortify/
├── frontend/                 # Next.js 프론트엔드
│   └── src/
│       ├── app/              # App Router 페이지 (/, /history)
│       ├── components/       # Atomic Design 컴포넌트
│       │   ├── atoms/        # Logo
│       │   ├── molecules/    # VideoUploader, HighlightCard, VideoHistoryCard, ProcessingStatus
│       │   ├── organisms/    # Header, HighlightGrid, VideoPlayer
│       │   ├── templates/    # MainLayout
│       │   └── ui/           # shadcn/ui components
│       ├── services/         # API Client Layer
│       ├── store/            # Zustand Store
│       ├── types/            # TypeScript Types
│       └── lib/              # Utilities
│
├── backend/                  # FastAPI 백엔드
│   ├── src/
│   │   ├── api/              # FastAPI Routes
│   │   ├── services/         # Business Logic (Transcription, Highlight, Export)
│   │   ├── infrastructure/   # Database, Repository Pattern
│   │   ├── models/           # Pydantic Schemas
│   │   └── core/             # Config, Constants
│   ├── migrations/           # Alembic Migrations
│   └── uploads/              # 업로드 파일 저장
│
└── docs/                     # 문서
    ├── 02-design/            # API Spec, Data Model
    └── 04-report/            # PDCA 완료 보고서
```

## 보안

| 보안 조치 | 구현 내용 |
|-----------|----------|
| XSS Prevention | next/image + 도메인 화이트리스트 |
| File Validation | 확장자 + MIME Type + Size (2GB) |
| URL Validation | YouTube URL 패턴 검증 (5종) |
| Rate Limiting | 60 req / 60s per IP |
| CORS | localhost:3000 허용 |
| Input Sanitization | Pydantic Schema Validation |

## 제한사항 (MVP)

| 항목 | 현재 | 프로덕션 권장 |
|------|------|---------------|
| Rate Limit Storage | In-memory | Redis |
| Export Job Storage | In-memory | Redis/DB |
| Large File Chunking | FFmpeg 기반 | 분산 처리 |
| Authentication | None | JWT/OAuth |

## 향후 개선 사항

1. **테스트 코드**: Unit/Integration 테스트 추가
2. **CI/CD**: GitHub Actions 파이프라인
3. **Logging**: Structured Logging (structlog)
4. **Monitoring**: Prometheus + Grafana
5. **CDN**: 영상 파일 CDN 배포

## 문서

- [API Specification](docs/02-design/api-spec.md)
- [Data Model](docs/02-design/data-model.md)
- [PDCA Completion Report](docs/04-report/shortify.report.md)

## 라이선스

MIT
