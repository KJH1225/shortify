from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API 설정
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # 데이터베이스
    database_url: str = "sqlite+aiosqlite:///./shortify.db"

    # OpenAI
    openai_api_key: str = ""

    # 파일 업로드
    upload_dir: str = "./uploads"
    max_file_size: int = 2 * 1024 * 1024 * 1024  # 2GB

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
