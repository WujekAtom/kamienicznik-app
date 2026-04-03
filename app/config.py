from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    app_name: str = "Zarządzanie Najmem"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 dni
    magic_link_expire_days: int = 365

    # Database
    database_url: str

    # Upload
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10

    # SMTP
    smtp_host: str
    smtp_port: int = 465
    smtp_username: str
    smtp_password: str
    smtp_from_name: str = "Kamienicznik Administrator"
    smtp_from_address: str


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()