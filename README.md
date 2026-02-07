# Shortify

AI 기반 영상 하이라이트 자동 추출 서비스

## 주요 기능

- 영상 파일 업로드 및 분석
- YouTube URL 분석 지원
- AI가 하이라이트 구간 자동 탐지
- 숏폼 콘텐츠로 내보내기

## 기술 스택

### Frontend
- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS v4
- shadcn/ui
- Zustand (상태관리)

### Backend
- FastAPI (Python)
- SQLAlchemy
- OpenAI API

### 인프라
- Turborepo (모노레포)
- pnpm (패키지 매니저)

## 시작하기

### 사전 요구사항

- Node.js 20+
- Python 3.11+
- pnpm

### 설치

```bash
# 의존성 설치
pnpm install

# Backend Python 의존성 설치
cd backend && pip install -r requirements.txt
```

### 환경 변수 설정

```bash
# Frontend
cp frontend/.env.example frontend/.env.local

# Backend
cp backend/.env.example backend/.env
```

### 개발 서버 실행

```bash
# 전체 실행 (Frontend + Backend)
pnpm dev

# 개별 실행
pnpm dev:frontend  # Frontend만
pnpm dev:backend   # Backend만
```

### 접속

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 프로젝트 구조

```
shortify/
├── frontend/                 # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/              # App Router 페이지
│   │   ├── components/       # Atomic Design 컴포넌트
│   │   │   ├── atoms/
│   │   │   ├── molecules/
│   │   │   ├── organisms/
│   │   │   └── templates/
│   │   ├── store/            # Zustand 스토어
│   │   └── types/            # TypeScript 타입
│   └── mocks/                # 목업 데이터
│
├── backend/                  # FastAPI 백엔드
│   └── src/
│       ├── api/              # API 라우터
│       ├── core/             # 설정
│       ├── models/           # Pydantic 스키마
│       └── services/         # 비즈니스 로직
│
├── turbo.json                # Turborepo 설정
└── pnpm-workspace.yaml       # pnpm 워크스페이스
```

## 라이선스

MIT
