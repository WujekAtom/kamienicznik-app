from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Zarządzanie Najmem"
    secret_key: str = "change-me-in-production-use-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 dni
    magic_link_expire_days: int = 365

    # Database
    database_url: str = "postgresql+asyncpg://rental:rental@db:5432/rental"
    postgres_user: str = "rental"
    postgres_password: str = "rental"
    postgres_db: str = "rental"

    # Upload
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10

    # SMTP
    SMTP_HOST: str = "smtp.wp.pl"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_NAME: str
    SMTP_FROM_ADDRESS: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    # model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()

# @lru_cache
def get_settings() -> Settings:
    return settings
