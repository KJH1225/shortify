from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API 설정
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # 데이터베이스
    # MySQL: mysql+aiomysql://user:password@localhost:3306/shortify
    # SQLite: sqlite+aiosqlite:///./shortify.db
    database_url: str = "sqlite+aiosqlite:///./shortify.db"

    # OpenAI
    openai_api_key: str = ""
    openai_whisper_model: str = "whisper-1"
    openai_chat_model: str = "gpt-4o"

    # AI 분석 설정
    audio_sample_rate: int = 16000
    whisper_chunk_size_mb: int = 24
    whisper_parallel_chunks: int = 10
    max_highlights: int = 10
    ai_retry_count: int = 3
    ai_retry_delay: float = 2.0

    # Multimodal analysis
    keyframe_interval: int = 10
    keyframe_max_count: int = 30
    keyframe_width: int = 512
    scene_threshold: float = 0.3
    audio_hotspot_count: int = 10

    # Highlight quality improvements
    crossfade_duration: float = 0.3
    snap_tolerance: float = 2.0
    loudness_shift_threshold: float = 10.0

    def has_openai_key(self) -> bool:
        """OpenAI API 키가 설정되었는지 확인"""
        return bool(self.openai_api_key and self.openai_api_key.strip())

    # 파일 업로드
    upload_dir: str = "./uploads"
    max_file_size: int = 2 * 1024 * 1024 * 1024  # 2GB

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    export_job_ttl_seconds: int = 24 * 60 * 60

    # Rate Limiting
    rate_limit_requests: int = 60
    rate_limit_window: int = 60

    class Config:
        env_file = "../.env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
