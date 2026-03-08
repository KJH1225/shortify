from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from api import videos, highlights, stream
from infrastructure.database import init_db, close_db
from infrastructure.redis_client import init_redis, close_redis, get_redis
from core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup: DB/Redis 연결 확인
    await init_db()
    await init_redis()
    yield
    # Shutdown: 연결 종료
    await close_redis()
    await close_db()


app = FastAPI(
    title="Shortify API",
    description="AI 영상 하이라이트 추출 서비스 API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Redis 기반 Rate Limiting 미들웨어"""
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    redis = get_redis()
    key = f"rate_limit:{client_ip}"

    current_time = await redis.time()
    now_seconds = current_time[0]
    window_start = now_seconds - settings.rate_limit_window

    await redis.zremrangebyscore(key, "-inf", window_start)
    request_count = await redis.zcard(key)

    if request_count >= settings.rate_limit_requests:
        return JSONResponse(
            status_code=429,
            content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."},
        )

    member = f"{now_seconds}:{current_time[1]}"
    score = now_seconds + (current_time[1] / 1_000_000)
    await redis.zadd(key, {member: score})
    await redis.expire(key, settings.rate_limit_window)

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
app.include_router(stream.router, prefix="/api", tags=["stream"])


@app.get("/")
async def root():
    return {"message": "Shortify API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
