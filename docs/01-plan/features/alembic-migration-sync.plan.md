# Plan: alembic-migration-sync

> Feature: Alembic 마이그레이션과 ORM 모델 동기화
> Created: 2026-02-08
> Level: Dynamic

## 1. 배경

현재 프로젝트에 두 가지 DB 스키마 정의 경로가 존재하며 **서로 불일치** 상태:

| 항목 | Alembic 마이그레이션 (`001`) | ORM 모델 (`models.py`) |
|------|---------------------------|----------------------|
| `videos.id` | `String(36)` (UUID) | `MySQLInteger(unsigned=True)` (AUTO_INCREMENT) |
| `highlights.id` | `String(36)` (UUID) | `MySQLInteger(unsigned=True)` (AUTO_INCREMENT) |
| `highlights.video_id` | `String(36)` FK | `MySQLInteger(unsigned=True)` FK |
| 인덱스 | `ix_videos_status`, `ix_videos_created_at`, `ix_highlights_video_id`, `ix_highlights_score` | 없음 |

### 현재 동작 방식

- 서버 시작 시 `init_db()` → `Base.metadata.create_all` 호출
- **ORM 모델 기준**으로 테이블 생성 (정수형 id, 인덱스 없음)
- Alembic 마이그레이션은 **실제로 사용되지 않는** 상태
- `alembic_version` 테이블도 생성되지 않으므로 마이그레이션 이력 추적 불가

### 왜 문제인가

1. **스키마 변경 관리 불가**: `create_all`은 새 컬럼 추가/타입 변경을 반영하지 못함
2. **마이그레이션 불일치**: Alembic 파일을 실행하면 UUID 기반 테이블이 생성되어 ORM과 충돌
3. **인덱스 누락**: ORM 모델에 인덱스 정의 없음 → 운영 시 쿼리 성능 저하
4. **팀 협업/배포 리스크**: 다른 환경에서 Alembic 실행 시 의도와 다른 스키마 생성

## 2. 목표

Alembic 마이그레이션을 ORM 모델(`models.py`)과 **완전 동기화**하여, Alembic이 유일한 스키마 관리 수단이 되도록 정비

## 3. 요구사항

### 3.1 마이그레이션 파일 재작성

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| M-1 | 기존 `001_initial_schema.py` 삭제 후 ORM 모델 기준으로 재생성 | P0 |
| M-2 | `id` 컬럼: `MySQLInteger(unsigned=True)` AUTO_INCREMENT로 통일 | P0 |
| M-3 | `video_id` FK: `MySQLInteger(unsigned=True)` 타입 일치 | P0 |
| M-4 | Enum 처리: `values_callable`로 소문자 값 사용 (ORM과 동일) | P0 |

### 3.2 인덱스 추가

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| I-1 | `videos.status` 인덱스 (ORM 모델 + 마이그레이션 양쪽) | P1 |
| I-2 | `videos.created_at` 인덱스 | P1 |
| I-3 | `highlights.video_id` 인덱스 | P1 |
| I-4 | `highlights.score` 인덱스 | P2 |

### 3.3 시작 방식 변경

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| S-1 | `init_db()`에서 `create_all` 제거 | P0 |
| S-2 | 서버 시작 시 Alembic `upgrade head` 자동 실행 또는 수동 운영 가이드 제공 | P1 |

### 3.4 Alembic 설정 정비

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| A-1 | `alembic.ini`의 `sqlalchemy.url`이 `.env` 기반으로 오버라이드되는지 확인 (현재 `env.py`에서 처리 중 → OK) | P0 |
| A-2 | MySQL 드라이버(`aiomysql`) 비동기 마이그레이션 정상 동작 확인 | P0 |

## 4. 현재 코드 분석

### 수정 대상

| 파일 | 현재 상태 | 변경 내용 |
|------|----------|----------|
| `migrations/versions/001_initial_schema.py` | UUID String(36) 기반 | 삭제 후 ORM 기준 재생성 |
| `backend/src/infrastructure/database.py` | `create_all` 사용 | `create_all` 제거, Alembic 위임 |
| `backend/src/infrastructure/models.py` | 인덱스 정의 없음 | `index=True` 또는 `Index()` 추가 |
| `backend/src/main.py` | `init_db()` 호출 | Alembic 방식으로 전환 |

### 유지 (변경 없음)

| 파일 | 이유 |
|------|------|
| `migrations/env.py` | 이미 비동기 + `.env` 연동 정상 |
| `alembic.ini` | `env.py`에서 URL 오버라이드 처리 중 |
| `backend/src/core/config.py` | 변경 없음 |
| `frontend/*` | 백엔드 전용 작업 |

## 5. 구현 범위

### In Scope
- 기존 마이그레이션 `001` 삭제 및 ORM 기준 재생성 (`alembic revision --autogenerate`)
- ORM 모델에 인덱스 정의 추가
- `init_db()`에서 `create_all` 제거
- 기존 DB 환경에서의 마이그레이션 적용 가이드

### Out of Scope
- DB 데이터 마이그레이션 (기존 데이터 보존은 별도 판단)
- 프로덕션 배포 자동화
- CI/CD 파이프라인 연동

## 6. 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| 마이그레이션 | Alembic | 이미 설치됨 |
| ORM | SQLAlchemy 2.0+ | `declarative_base` 사용 중 |
| DB | MySQL 8.x + `aiomysql` | `.env`에 설정됨 |
| 비동기 | `async_engine_from_config` | `env.py`에 구현됨 |

## 7. 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/src/infrastructure/models.py` | 인덱스 정의 추가 (`index=True`) |
| `backend/src/infrastructure/database.py` | `create_all` 제거, `init_db()` 변경 |
| `backend/src/main.py` | `init_db()` 호출 방식 변경 |
| `backend/migrations/versions/001_initial_schema.py` | 삭제 |
| `backend/migrations/versions/XXX_initial_schema_v2.py` | ORM 기준 신규 생성 |

## 8. 리스크

| 리스크 | 완화 방안 |
|--------|----------|
| 기존 DB 테이블과 새 마이그레이션 충돌 | `alembic stamp head`로 현재 상태 마킹 후 진행 |
| 데이터 유실 | 작업 전 DB 백업 필수, `drop_all` 절대 금지 |
| MySQL과 Alembic autogenerate 호환 | MySQL dialect 확인, 테스트 환경에서 먼저 실행 |
| `create_all` 제거 후 빈 DB 시작 불가 | `alembic upgrade head` 실행 가이드 문서화 |
| Alembic 버전 테이블 부재 | `alembic stamp head`로 초기화 |

## 9. 작업 순서

1. **DB 백업** (현재 MySQL 데이터)
2. ORM 모델에 인덱스 추가 (`models.py`)
3. 기존 마이그레이션 `001` 삭제
4. `alembic revision --autogenerate -m "initial_schema_v2"` 실행
5. 생성된 마이그레이션 검증 (ORM과 일치 확인)
6. 기존 DB에 `alembic stamp head` 실행 (현 상태를 최신으로 마킹)
7. `database.py`에서 `create_all` 제거
8. `main.py`의 `init_db()` 정리
9. 서버 재시작 후 정상 동작 확인
