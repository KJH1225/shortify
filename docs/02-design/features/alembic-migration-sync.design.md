# Design: alembic-migration-sync

> Feature: Alembic 마이그레이션과 ORM 모델 동기화
> Plan: [alembic-migration-sync.plan.md](../../01-plan/features/alembic-migration-sync.plan.md)
> Created: 2026-02-08
> Level: Dynamic

## 1. 설계 개요

Alembic 마이그레이션 파일을 ORM 모델(`models.py`) 기준으로 재작성하고, `create_all` 기반 초기화를 제거하여 Alembic을 유일한 스키마 관리 수단으로 전환한다.

## 2. 변경 파일 및 상세 설계

### 2.1 `backend/src/infrastructure/models.py` - 인덱스 추가

**현재 코드** (변경 대상 부분만):

```python
# Video
id = Column(MySQLInteger(unsigned=True), primary_key=True, autoincrement=True)
# ... (인덱스 없음)
created_at = Column(DateTime, default=datetime.now, nullable=False)
updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Highlight
id = Column(MySQLInteger(unsigned=True), primary_key=True, autoincrement=True)
video_id = Column(MySQLInteger(unsigned=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
# ... (인덱스 없음)
```

**변경 후:**

```python
class Video(Base):
    """Video table"""
    __tablename__ = "videos"

    id = Column(MySQLInteger(unsigned=True), primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)

    source_type = Column(String(20), nullable=False)
    source_url = Column(String(512), nullable=True)
    source_filename = Column(String(255), nullable=True)

    duration = Column(Float, nullable=True)
    status = Column(
        SQLEnum(ProcessingStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ProcessingStatus.IDLE,
        index=True,                    # [I-1] 추가
    )
    progress = Column(Integer, default=0)
    message = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)   # [I-2] 추가
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    highlights = relationship("Highlight", back_populates="video", cascade="all, delete-orphan")


class Highlight(Base):
    """Highlight table"""
    __tablename__ = "highlights"

    id = Column(MySQLInteger(unsigned=True), primary_key=True, autoincrement=True)
    video_id = Column(
        MySQLInteger(unsigned=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,                    # [I-3] 추가
    )

    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    score = Column(Float, nullable=False, index=True)   # [I-4] 추가
    thumbnail_url = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)

    video = relationship("Video", back_populates="highlights")
```

**변경 요약:**

| 컬럼 | 추가 속성 | 요구사항 |
|------|----------|---------|
| `Video.status` | `index=True` | I-1 |
| `Video.created_at` | `index=True` | I-2 |
| `Highlight.video_id` | `index=True` | I-3 |
| `Highlight.score` | `index=True` | I-4 |

---

### 2.2 `backend/src/infrastructure/database.py` - `create_all` 제거

**현재 코드:**

```python
async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**변경 후:**

```python
async def init_db():
    """Verify database connection on startup.
    Schema management is handled by Alembic migrations.
    Run: cd backend && alembic upgrade head
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
```

**설계 의도:**
- `create_all` 제거 → 스키마 생성은 Alembic에 위임 [S-1]
- 연결 확인(`SELECT 1`)은 유지 → 서버 시작 시 DB 접속 불가 상태를 즉시 감지
- `text` import 추가 필요: `from sqlalchemy import text`

---

### 2.3 `backend/src/main.py` - lifespan 변경

**현재 코드:**

```python
from infrastructure.database import init_db, close_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup: DB 초기화
    await init_db()
    yield
    # Shutdown: DB 연결 종료
    await close_db()
```

**변경 후:**

```python
from infrastructure.database import init_db, close_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup: DB 연결 확인 (스키마는 Alembic으로 관리)
    await init_db()
    yield
    # Shutdown: DB 연결 종료
    await close_db()
```

**변경점:** 주석만 변경. `init_db()` 함수 자체가 변경되므로 호출부는 동일 유지.

---

### 2.4 마이그레이션 파일 교체

#### 2.4.1 삭제 대상

```
backend/migrations/versions/20260208_0100_001_initial_schema.py
```

#### 2.4.2 신규 생성 (autogenerate)

**실행 명령:**

```bash
cd backend && alembic revision --autogenerate -m "initial_schema_v2"
```

**예상 생성 결과** (autogenerate 기반, MySQL dialect):

```python
"""initial_schema_v2

Revision ID: 002
Revises:
Create Date: 2026-02-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '002'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'videos',
        sa.Column('id', mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('source_filename', sa.String(length=255), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('idle', 'uploading', 'processing', 'completed', 'error', name='processingstatus'), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_videos_status', 'videos', ['status'])
    op.create_index('ix_videos_created_at', 'videos', ['created_at'])

    op.create_table(
        'highlights',
        sa.Column('id', mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('video_id', mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_highlights_video_id', 'highlights', ['video_id'])
    op.create_index('ix_highlights_score', 'highlights', ['score'])


def downgrade() -> None:
    op.drop_index('ix_highlights_score', table_name='highlights')
    op.drop_index('ix_highlights_video_id', table_name='highlights')
    op.drop_table('highlights')

    op.drop_index('ix_videos_created_at', table_name='videos')
    op.drop_index('ix_videos_status', table_name='videos')
    op.drop_table('videos')
```

**핵심 차이점 (기존 001 vs 신규 002):**

| 항목 | 기존 001 | 신규 002 |
|------|---------|---------|
| `id` 타입 | `String(36)` | `mysql.INTEGER(unsigned=True)` |
| `video_id` 타입 | `String(36)` | `mysql.INTEGER(unsigned=True)` |
| PK 방식 | UUID 문자열 | AUTO_INCREMENT 정수 |
| Enum | 직접 지정 | ORM과 동일 (`values_callable` 반영) |
| 인덱스 | 4개 | 4개 (동일) |

---

## 3. 기존 DB 환경 마이그레이션 전략

현재 DB에 이미 ORM `create_all`로 생성된 테이블이 있으므로:

```
Step 1: 기존 마이그레이션 001 삭제
Step 2: ORM에 인덱스 추가
Step 3: autogenerate로 새 마이그레이션 생성
Step 4: alembic stamp head  ← 핵심 (현재 DB를 최신으로 마킹)
Step 5: database.py에서 create_all 제거
```

`alembic stamp head`는 실제 SQL을 실행하지 않고, `alembic_version` 테이블에 현재 revision만 기록한다. 이미 테이블이 존재하는 환경에서 마이그레이션 이력을 초기화하는 표준 방법이다.

### 인덱스 처리

`stamp head`는 DDL을 실행하지 않으므로, 기존 DB에는 인덱스가 없는 상태가 된다. 별도로 인덱스를 수동 추가하거나, 이후 마이그레이션에서 인덱스만 추가하는 revision을 생성할 수 있다.

**권장 방법:** `stamp head` 후 인덱스 추가 마이그레이션을 별도 생성

```bash
# stamp 후 ORM과 DB 차이 감지 → 인덱스 추가 마이그레이션 자동 생성
alembic revision --autogenerate -m "add_indexes"
alembic upgrade head
```

## 4. 구현 순서 (체크리스트)

| 순서 | 작업 | 파일 | 요구사항 |
|------|------|------|---------|
| 1 | DB 백업 (mysqldump) | - | 리스크 완화 |
| 2 | ORM 모델에 `index=True` 추가 | `models.py` | I-1~I-4 |
| 3 | 기존 마이그레이션 `001` 파일 삭제 | `migrations/versions/` | M-1 |
| 4 | `alembic revision --autogenerate` 실행 | `migrations/versions/` | M-1~M-4 |
| 5 | 생성된 마이그레이션 검증 (ORM 일치 확인) | - | M-2~M-4 |
| 6 | `alembic stamp head` 실행 | - | 기존 DB 마킹 |
| 7 | `database.py` 수정 (`create_all` → `SELECT 1`) | `database.py` | S-1 |
| 8 | `main.py` 주석 수정 | `main.py` | S-2 |
| 9 | 서버 재시작 및 동작 확인 | - | A-2 |
| 10 | (선택) 인덱스 마이그레이션 생성 및 적용 | `migrations/versions/` | I-1~I-4 |

## 5. 검증 기준

| ID | 검증 항목 | 통과 조건 |
|----|----------|----------|
| V-1 | `models.py`에 `index=True` 4개 추가 | `status`, `created_at`, `video_id`, `score` |
| V-2 | 기존 `001` 마이그레이션 파일 삭제됨 | 파일 부재 확인 |
| V-3 | 새 마이그레이션 파일의 `id` 타입이 `mysql.INTEGER(unsigned=True)` | autogenerate 결과 확인 |
| V-4 | 새 마이그레이션에 인덱스 4개 포함 | `ix_videos_status`, `ix_videos_created_at`, `ix_highlights_video_id`, `ix_highlights_score` |
| V-5 | `database.py`에 `create_all` 없음 | 코드 확인 |
| V-6 | `database.py`에 `SELECT 1` 연결 확인 존재 | 코드 확인 |
| V-7 | `alembic_version` 테이블에 최신 revision 기록됨 | DB 확인 |
| V-8 | 서버 정상 시작 (`/health` 200 OK) | curl 확인 |
| V-9 | 기존 데이터 보존됨 | `SELECT COUNT(*) FROM videos` 확인 |
| V-10 | `alembic current` 출력이 head와 일치 | 터미널 확인 |
