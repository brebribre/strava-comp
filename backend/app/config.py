from functools import lru_cache

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

    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
