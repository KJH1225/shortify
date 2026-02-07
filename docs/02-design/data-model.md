# Shortify Data Model Specification

> Version: 0.1.0
> Database: MySQL / SQLite (async)

---

## Overview

Shortify의 데이터 모델은 영상(Video)과 하이라이트(Highlight) 두 개의 주요 엔티티로 구성됩니다.

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────┐
│              Video                  │
├─────────────────────────────────────┤
│ id: string(36) [PK]                 │
│ title: string(255)                  │
│ source_type: string(20)             │
│ source_url: string(512)?            │
│ source_filename: string(255)?       │
│ duration: float?                    │
│ status: enum(ProcessingStatus)      │
│ progress: int                       │
│ message: text                       │
│ created_at: datetime                │
│ updated_at: datetime                │
└─────────────────────────────────────┘
                │
                │ 1:N
                ▼
┌─────────────────────────────────────┐
│            Highlight                │
├─────────────────────────────────────┤
│ id: string(36) [PK]                 │
│ video_id: string(36) [FK]           │
│ start_time: float                   │
│ end_time: float                     │
│ title: string(255)                  │
│ description: text?                  │
│ score: float                        │
│ thumbnail_url: string(512)?         │
│ created_at: datetime                │
└─────────────────────────────────────┘
```

---

## Entities

### Video

영상 정보를 저장하는 메인 엔티티

| Column | Type | Nullable | Default | Description |
|--------|------|:--------:|---------|-------------|
| `id` | VARCHAR(36) | No | - | UUID, Primary Key |
| `title` | VARCHAR(255) | No | - | 영상 제목 |
| `source_type` | VARCHAR(20) | No | - | 소스 타입 (`file`, `youtube`) |
| `source_url` | VARCHAR(512) | Yes | NULL | YouTube URL (youtube 타입일 때) |
| `source_filename` | VARCHAR(255) | Yes | NULL | 파일명 (file 타입일 때) |
| `duration` | FLOAT | Yes | NULL | 영상 길이 (초) |
| `status` | ENUM | No | `idle` | 처리 상태 |
| `progress` | INT | No | 0 | 진행률 (0-100) |
| `message` | TEXT | Yes | NULL | 상태 메시지 |
| `created_at` | DATETIME | No | NOW() | 생성 일시 |
| `updated_at` | DATETIME | No | NOW() | 수정 일시 |

**Indexes**:
- `PRIMARY KEY (id)`
- `INDEX (status)` - 상태별 조회 최적화
- `INDEX (created_at)` - 최신순 정렬 최적화

---

### Highlight

추출된 하이라이트 구간 정보

| Column | Type | Nullable | Default | Description |
|--------|------|:--------:|---------|-------------|
| `id` | VARCHAR(36) | No | - | UUID, Primary Key |
| `video_id` | VARCHAR(36) | No | - | Foreign Key → Video.id |
| `start_time` | FLOAT | No | - | 시작 시간 (초) |
| `end_time` | FLOAT | No | - | 종료 시간 (초) |
| `title` | VARCHAR(255) | No | - | 하이라이트 제목 |
| `description` | TEXT | Yes | NULL | 상세 설명 |
| `score` | FLOAT | No | 0.0 | AI 점수 (0.0 ~ 1.0) |
| `thumbnail_url` | VARCHAR(512) | Yes | NULL | 썸네일 이미지 URL |
| `created_at` | DATETIME | No | NOW() | 생성 일시 |

**Indexes**:
- `PRIMARY KEY (id)`
- `FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE`
- `INDEX (video_id)` - 영상별 하이라이트 조회 최적화
- `INDEX (score DESC)` - 점수순 정렬 최적화

---

## Enums

### ProcessingStatus

영상 처리 상태를 나타내는 열거형

```python
class ProcessingStatus(str, Enum):
    IDLE = "idle"           # 초기 상태
    UPLOADING = "uploading" # 업로드 중
    PROCESSING = "processing" # AI 분석 중
    COMPLETED = "completed" # 완료
    ERROR = "error"         # 오류
```

---

## Relationships

### Video → Highlight (1:N)

- 하나의 Video는 여러 Highlight를 가질 수 있음
- Video 삭제 시 관련 Highlight도 함께 삭제 (CASCADE)

```python
# Video Model
highlights = relationship("HighlightModel", back_populates="video", cascade="all, delete-orphan")

# Highlight Model
video = relationship("VideoModel", back_populates="highlights")
```

---

## SQLAlchemy Model Definitions

### VideoModel

```python
class VideoModel(Base):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    source_type = Column(String(20), nullable=False)
    source_url = Column(String(512), nullable=True)
    source_filename = Column(String(255), nullable=True)
    duration = Column(Float, nullable=True)
    status = Column(SQLEnum(ProcessingStatus), nullable=False, default=ProcessingStatus.IDLE)
    progress = Column(Integer, nullable=False, default=0)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    highlights = relationship("HighlightModel", back_populates="video", cascade="all, delete-orphan")
```

### HighlightModel

```python
class HighlightModel(Base):
    __tablename__ = "highlights"

    id = Column(String(36), primary_key=True)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    score = Column(Float, nullable=False, default=0.0)
    thumbnail_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("VideoModel", back_populates="highlights")
```

---

## Pydantic Schemas

### Request Schemas

```python
class YouTubeURLRequest(BaseModel):
    url: str
```

### Response Schemas

```python
class VideoSource(BaseModel):
    type: str  # "file" | "youtube"
    url: str | None = None
    filename: str | None = None

class HighlightResponse(BaseModel):
    id: str
    video_id: str
    start_time: float
    end_time: float
    title: str
    description: str | None = None
    score: float
    thumbnail_url: str | None = None
    created_at: datetime

class VideoResponse(BaseModel):
    id: str
    title: str
    source: VideoSource
    duration: float | None = None
    status: ProcessingStatus
    progress: int
    message: str | None = None
    highlights: list[HighlightResponse] = []
    created_at: datetime
    updated_at: datetime
```

---

## Database Configuration

### Connection Settings

```python
# SQLite (Development)
DATABASE_URL = "sqlite+aiosqlite:///./shortify.db"

# MySQL (Production)
DATABASE_URL = "mysql+aiomysql://user:password@host:3306/shortify"
```

### Pool Settings

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)
```

---

## Migration Notes

### Initial Schema (v0.1.0)

```sql
-- Videos Table
CREATE TABLE videos (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_url VARCHAR(512),
    source_filename VARCHAR(255),
    duration FLOAT,
    status ENUM('idle', 'uploading', 'processing', 'completed', 'error') NOT NULL DEFAULT 'idle',
    progress INT NOT NULL DEFAULT 0,
    message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Highlights Table
CREATE TABLE highlights (
    id VARCHAR(36) PRIMARY KEY,
    video_id VARCHAR(36) NOT NULL,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    score FLOAT NOT NULL DEFAULT 0.0,
    thumbnail_url VARCHAR(512),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    INDEX idx_video_id (video_id),
    INDEX idx_score (score DESC)
);
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-08 | Initial data model specification |
