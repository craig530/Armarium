import logging
import secrets
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("armarium")

# Bumped by hand alongside frontend/package.json's "version" at each release
# — there's no build-time step that derives one from the other.
APP_VERSION = "1.10.0"


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/armarium.db"

    # Auth
    jwt_secret: str = ""              # required in production — set via .env
    jwt_expire_minutes: int = 60 * 24 * 7     # 7 days

    # Set the `Secure` flag on the access-token cookie (requires HTTPS).
    # Only disable for HTTP-only deployments (e.g. an internal network
    # without TLS) — without it, the cookie is sent over plain HTTP.
    cookie_secure: bool = True

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
    igdb_client_id: Optional[str] = None
    igdb_client_secret: Optional[str] = None
    # Optional second fallback for barcode-to-title resolution (films/TV and
    # games flows), only queried when UPCitemdb has no match for the code.
    upcdatabase_api_key: Optional[str] = None

    # CORS — comma-separated origins, or * for all. Empty = same-origin only.
    cors_origins: str = "*"

    # Host port the web UI is served on (docker-compose's `PORT` mapping —
    # see .env.example). Purely informational here: the container itself
    # always listens on a fixed internal port regardless of this value; it's
    # surfaced via /admin/system-info so admins can see the configured host
    # port even when accessing the app through a reverse proxy on a
    # different external port.
    port: str = "8080"

    # SMTP — required for user invites and password-reset emails. Features
    # that need to send mail return 503 (see services/email.is_configured)
    # when smtp_host is unset, the same "not configured" posture as the
    # TMDB/IGDB integrations.
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    # Sender address for outgoing mail — falls back to smtp_username if unset.
    smtp_from_address: Optional[str] = None
    smtp_use_tls: bool = True

    # Overrides the host used to build set-password/reset links in emails.
    # Unset by default: the triggering request's own Host header (this app
    # is always single-origin behind one reverse proxy, per ARCHITECTURE.md
    # §3) is normally correct. Only needed if that's somehow wrong.
    public_base_url: Optional[str] = None

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
