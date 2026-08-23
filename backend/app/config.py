from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://strava:strava@localhost:5433/strava"

    strava_client_id: str = ""
    strava_client_secret: str = ""

    # Used later for signed session cookies (Phase 3) and webhook verification (Phase 7).
    secret_key: str = "dev-secret-change-me"
    strava_verify_token: str = "dev-verify-token"

    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
