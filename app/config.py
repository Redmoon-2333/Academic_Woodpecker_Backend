from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    SECRET_KEY: str = "academic-woodpecker-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    ECNU_API_KEY: str = ""
    ECNU_API_BASE: str = "https://chat.ecnu.edu.cn/open/api/v1"
    LLM_MODEL: str = "ecnu-plus"

    # LangFuse observability (optional)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    UPLOAD_DIR: str = "app/uploads"
    ALLOWED_EXTENSIONS: set = {"pdf", "jpg", "jpeg", "png", "txt"}
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    class Config:
        env_file = ".env"


settings = Settings()
