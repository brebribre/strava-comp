from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://strava:strava@localhost:5433/strava"

    # --- Strava app credentials (strava.com/settings/api) ---
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/auth/strava/callback"
    # activity:read_all is needed to see private activities too.
    strava_scope: str = "read,activity:read_all"

    # Used for webhook verification (Phase 7).
    strava_verify_token: str = "dev-verify-token"

    # --- Sessions ---
    secret_key: str = "dev-secret-change-me"
    session_cookie_name: str = "sgt_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 30  # 30 days
    # Must be True in production (HTTPS); False locally so the cookie works over http.
    cookie_secure: bool = False
    # "lax" is right when frontend and backend share a site. When they are on different
    # domains (Vercel frontend + Railway backend) it must be "none", which browsers only
    # honour together with Secure=true.
    cookie_samesite: str = "lax"

    # How far back to pull activities on first login.
    backfill_days: int = 7

    log_level: str = "INFO"

    # From @BotFather. Empty disables Telegram notifications entirely.
    telegram_bot_token: str = ""

    frontend_origin: str = "http://localhost:5173"
    # Comma-separated extra origins allowed by CORS, e.g. a Railway preview URL.
    extra_cors_origins: str = ""

    @field_validator("database_url")
    @classmethod
    def _use_psycopg3_driver(cls, value: str) -> str:
        """Railway injects DATABASE_URL as `postgresql://…`.

        SQLAlchemy reads that as psycopg2, which isn't installed. Rewriting the scheme
        here means the platform-provided variable works unmodified.
        """
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.frontend_origin]
        origins += [o.strip() for o in self.extra_cors_origins.split(",") if o.strip()]
        return list(dict.fromkeys(origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()
