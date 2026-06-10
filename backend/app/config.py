from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/armarium.db"

    # Auth
    jwt_secret: str = secrets.token_hex(32)   # overridden by .env in production
    jwt_expire_minutes: int = 60 * 24 * 7     # 7 days

    # Default admin (created on first run if no users exist)
    admin_username: str = "admin"
    admin_password: str = "changeme"

    # Storage
    covers_dir: str = "./data/covers"
    backup_dir: str = "./data/backups"

    # External APIs
    tmdb_api_key: Optional[str] = None

    # CORS — comma-separated origins, or * for all
    cors_origins: str = "*"

    class Config:
        env_file = ".env"


settings = Settings()
