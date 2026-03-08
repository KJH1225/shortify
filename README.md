# Shortify

AI가 긴 영상에서 재미있는 부분을 자동으로 찾아 숏폼 영상으로 만들어주는 서비스

> **버전**: 0.4.1

## 주요 기능

| 기능 | 설명 |
|------|------|
| 영상 업로드 | 파일 직접 업로드 (mp4, mov 등) |
| YouTube 지원 | YouTube 링크 붙여넣기 (일반, shorts, live 모두 가능) |
| AI 하이라이트 추출 | 음성 인식 + GPT-4o가 재미있는 구간 자동 선택 |
| 멀티모달 분석 | 말(텍스트) + 화면(이미지) + 소리(오디오) + 장면 전환을 종합 분석 |
| 똑똑한 키프레임 | 중요한 순간의 화면을 골라서 GPT에게 보여줌 |
| 소리 감정 분석 | 볼륨 급상승, 무음→말하기 전환, 분위기 변화 감지 |
| 문장 단위 자르기 | 말 중간에 안 잘리고 문장이 끝나는 지점에서 자름 |
| 맥락 자동 포함 | 각 클립 앞에 "이건 무슨 이야기야" 부분을 자동 추가 |
| 부드러운 전환 | 장면이 바뀔 때 뚝 끊기지 않고 부드럽게 이어짐 |
| 숏폼 레이아웃 | 세로(9:16) 화면에 맞게 자동 변환 (배경 블러 처리) |
| 영상 플레이어 | 하이라이트 구간 미리보기 |
| 영상 기록 | 이전에 분석한 영상 다시 보기, 삭제 |
| 숏폼 다운로드 | 편집된 숏폼 영상을 mp4로 다운로드 |
| 실시간 상태 | 분석 진행률 실시간 확인 |

## 어떻게 동작하나?

```
영상을 넣으면
  |
  +-> 소리를 뽑아서
  |     |
  |     +-> AI가 말을 텍스트로 바꾸고 (음성 인식)
  |     +-> 소리가 갑자기 커지는 곳을 찾고 (볼륨 분석)
  |     +-> 분위기가 바뀌는 곳을 찾음 (감정 분석)
  |
  +-> 화면이 바뀌는 장면을 찾고 (장면 전환)
  |
  +-> 중요한 순간의 화면을 캡처해서 (키프레임)
        |
  GPT-4o에게 전부 보여주면
  "이 부분이 재미있어!" 하고 골라줌
        |
  문장 끝에 맞춰서 깔끔하게 자르고
        |
  앞에 맥락("이건 ~에 대한 이야기야")을 붙이고
        |
  저장
        |
  다운로드하면: 부드러운 전환 효과 넣어서 영상 생성
```

## 기술 스택

### 화면 (Frontend)
- **Next.js 15** - 웹 화면
- **TypeScript** - 타입 안전한 코드
- **Tailwind CSS v4** - 스타일링
- **shadcn/ui** - UI 부품
- **Zustand** - 상태 관리

### 서버 (Backend)
- **FastAPI** - Python 웹 서버
- **SQLAlchemy 2.0** - 데이터베이스 연결
- **MySQL / SQLite** - 데이터 저장
- **Alembic** - DB 버전 관리
- **Redis** - 요청 제한, 작업 관리
- **FFmpeg** - 영상 처리 (자르기, 합치기, 소리 분석 등)

### AI
- **OpenAI Whisper** - 음성을 텍스트로 변환
- **OpenAI GPT-4o** - 하이라이트 구간 분석 (텍스트 + 이미지 동시 이해)

## 시작하기

### 필요한 것

- Node.js 20 이상
- Python 3.13 이상
- pnpm
- FFmpeg
- Redis
- MySQL 8.0 이상 (개발 시 SQLite 사용 가능)

### FFmpeg 설치

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
choco install ffmpeg
```

### 설치

```bash
# 1. 패키지 설치
pnpm install

# 2. Python 환경 설정
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 환경 변수

**Frontend** (`frontend/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Backend** (`backend/.env`):
```env
DATABASE_URL=sqlite+aiosqlite:///./shortify.db
OPENAI_API_KEY=여기에-OpenAI-키-입력
OPENAI_CHAT_MODEL=gpt-4o
UPLOAD_DIR=./uploads
REDIS_URL=redis://localhost:6379/0
```

### DB 초기화

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

### 실행

```bash
# 한번에 실행
pnpm dev

# 또는 따로 실행
pnpm dev:frontend  # 화면 (3000번 포트)
pnpm dev:backend   # 서버 (8000번 포트)
```

### 접속

| 서비스 | 주소 |
|--------|------|
| 화면 | http://localhost:3000 |
| API 서버 | http://localhost:8000 |
| API 문서 | http://localhost:8000/docs |

## 설정값

### AI 분석 설정

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `OPENAI_CHAT_MODEL` | `gpt-4o` | AI 모델 |
| `MAX_HIGHLIGHTS` | `10` | 최대 하이라이트 수 |
| `KEYFRAME_INTERVAL` | `10` | 화면 캡처 간격 (초) |
| `KEYFRAME_MAX_COUNT` | `30` | 최대 캡처 수 |
| `SCENE_THRESHOLD` | `0.3` | 장면 전환 감도 (낮을수록 민감) |
| `AUDIO_HOTSPOT_COUNT` | `10` | 소리 이벤트 최대 수 |

### 숏폼 품질 설정

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `CROSSFADE_DURATION` | `0.3` | 장면 전환 효과 길이 (초), 0이면 끔 |
| `SNAP_TOLERANCE` | `2.0` | 문장 경계 맞춤 허용 범위 (초) |
| `LOUDNESS_SHIFT_THRESHOLD` | `10.0` | 분위기 변화 감지 민감도 |
| `CONTEXT_PADDING` | `3.0` | 맥락 추가 길이 (초), 0이면 끔 |
| `HIGHLIGHT_MIN_DURATION` | `30` | 하이라이트 최소 길이 (초) |
| `HIGHLIGHT_MAX_DURATION` | `55` | 하이라이트 최대 길이 (초) |

## API

### 영상
| 방식 | 주소 | 설명 |
|------|------|------|
| POST | `/api/videos/upload` | 영상 파일 올리기 |
| POST | `/api/videos/youtube` | YouTube 링크로 처리 |
| GET | `/api/videos/{id}` | 영상 정보 보기 |
| GET | `/api/videos/` | 영상 목록 보기 |
| GET | `/api/videos/{id}/stream` | 영상 재생 |
| DELETE | `/api/videos/{id}` | 영상 삭제 |

### 하이라이트
| 방식 | 주소 | 설명 |
|------|------|------|
| GET | `/api/highlights/{id}` | 하이라이트 보기 |
| POST | `/api/highlights/{id}/export` | 숏폼 만들기 |
| GET | `/api/highlights/{id}/export/{export_id}/status` | 만들기 진행 상태 |
| GET | `/api/highlights/{id}/export/{export_id}/download` | 숏폼 다운로드 |
| DELETE | `/api/highlights/{id}` | 하이라이트 삭제 |

## 프로젝트 구조

```
shortify/
├── frontend/                 # 화면
│   └── src/
│       ├── app/              # 페이지 (메인, 기록)
│       ├── components/       # UI 부품
│       ├── services/         # API 통신
│       ├── store/            # 상태 관리
│       └── types/            # 타입 정의
│
├── backend/                  # 서버
│   ├── src/
│   │   ├── api/              # API 주소 처리
│   │   ├── services/         # 핵심 로직
│   │   │   ├── video_processor.py      # 전체 분석 흐름 관리
│   │   │   ├── transcription_service.py # 음성 인식 (Whisper)
│   │   │   ├── highlight_analyzer.py    # GPT 하이라이트 분석 + 문장 자르기 + 맥락 추가
│   │   │   ├── audio_extractor.py       # 영상에서 소리 추출
│   │   │   ├── audio_analyzer.py        # 볼륨/분위기 분석
│   │   │   ├── keyframe_extractor.py    # 중요 장면 캡처
│   │   │   ├── scene_detector.py        # 장면 전환 감지
│   │   │   └── export_processor.py      # 숏폼 영상 생성 + 전환 효과
│   │   ├── infrastructure/   # DB, Redis 연결
│   │   ├── models/           # 데이터 형식
│   │   └── core/             # 설정, AI 지시문
│   ├── migrations/           # DB 변경 기록
│   └── uploads/              # 업로드된 파일
│
└── docs/                     # 문서
```

## 보안

| 항목 | 내용 |
|------|------|
| 파일 검증 | 확장자 + 파일 종류 + 크기(2GB 제한) 확인 |
| URL 검증 | YouTube 링크 6가지 형식만 허용 |
| 요청 제한 | IP당 1분에 60번까지 |
| 입력 검증 | 모든 입력값 형식 검사 |

## 현재 한계

| 항목 | 현재 | 개선 방향 |
|------|------|-----------|
| 로그인 | 없음 | 추가 필요 |
| 파일 정리 | 수동 삭제 | 자동 삭제 필요 |
| 대용량 처리 | 단일 서버 | 분산 처리 |

## 앞으로 할 것

1. 영상 상단 제목 텍스트 추가
2. 로컬에 직접 파일 다운 받는것 s3로 변경
3. 오래된 영상/숏폼 파일 자동 삭제
4. 같은 하이라이트 다시 다운로드 시 기존 파일 재사용

## 라이선스

MIT
