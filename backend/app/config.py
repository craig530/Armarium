import logging
import secrets
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("armarium")


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/armarium.db"

    # Auth
    jwt_secret: str = ""              # required in production — set via .env
    jwt_expire_minutes: int = 60 * 24 * 7     # 7 days

    # Default admin (created on first run if no users exist)
    admin_username: str = "admin"
    admin_password: str = "changeme"

    # Storage
    covers_dir: str = "./data/covers"
    backup_dir: str = "./data/backups"
    location_icons_dir: str = "./data/location_icons"
    platform_logos_dir: str = "./data/platform_logos"

    # External APIs
    tmdb_api_key: Optional[str] = None

    # CORS — comma-separated origins, or * for all. Empty = same-origin only.
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env")

    @model_validator(mode="after")
    def _ensure_jwt_secret(self):
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_hex(32)
            logger.warning(
                "JWT_SECRET is not set — using a randomly generated secret for this "
                "process only. All existing sessions will be invalidated on restart. "
                "Set JWT_SECRET in your .env file (generate with: openssl rand -hex 32)."
            )
        return self


settings = Settings()
