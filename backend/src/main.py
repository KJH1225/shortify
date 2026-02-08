from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict
import time
from contextlib import asynccontextmanager
from api import videos, highlights
from infrastructure.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup: DB 연결 확인 (스키마는 Alembic으로 관리)
    await init_db()
    yield
    # Shutdown: DB 연결 종료
    await close_db()


app = FastAPI(
    title="Shortify API",
    description="AI 영상 하이라이트 추출 서비스 API",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate Limiting 설정
RATE_LIMIT_REQUESTS = 60  # 요청 수
RATE_LIMIT_WINDOW = 60  # 초 단위 윈도우
rate_limit_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """간단한 Rate Limiting 미들웨어"""
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()

    # 윈도우 밖의 오래된 요청 제거
    rate_limit_store[client_ip] = [
        req_time for req_time in rate_limit_store[client_ip]
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]

    # Rate limit 체크
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."}
        )

    # 현재 요청 기록
    rate_limit_store[client_ip].append(current_time)

    response = await call_next(request)
    return response


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(highlights.router, prefix="/api/highlights", tags=["highlights"])


@app.get("/")
async def root():
    return {"message": "Shortify API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
