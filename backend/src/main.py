from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import videos, highlights

app = FastAPI(
    title="Shortify API",
    description="AI 영상 하이라이트 추출 서비스 API",
    version="0.1.0"
)

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
