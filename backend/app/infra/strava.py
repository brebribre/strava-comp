"""HTTP client for the Strava API.

Every outbound Strava call lives here, so services never touch httpx directly.
Phase 4 adds refresh_access_token; Phase 6 adds activity fetching.
"""

from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import get_settings

STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_OAUTH_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_OAUTH_TOKEN_URL = "https://www.strava.com/oauth/token"

TIMEOUT = httpx.Timeout(10.0)


class StravaError(RuntimeError):
    """Strava returned something we can't use."""


def build_authorize_url(state: str) -> str:
    """The URL a user is sent to in order to grant access."""
    settings = get_settings()
    params = {
        "client_id": settings.strava_client_id,
        "redirect_uri": settings.strava_redirect_uri,
        "response_type": "code",
        "scope": settings.strava_scope,
        # force ensures the scope prompt is shown again rather than silently
        # reusing a narrower grant from an earlier authorization.
        "approval_prompt": "force",
        "state": state,
    }
    return f"{STRAVA_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Trade a one-time authorization code for access/refresh tokens.

    Returns Strava's raw payload: access_token, refresh_token, expires_at (epoch
    seconds) and an `athlete` object.
    """
    settings = get_settings()
    try:
        response = httpx.post(
            STRAVA_OAUTH_TOKEN_URL,
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise StravaError(f"could not reach Strava: {exc}") from exc

    if response.status_code != httpx.codes.OK:
        # Never log the body verbatim elsewhere — it echoes the client secret on some errors.
        raise StravaError(f"token exchange failed ({response.status_code})")

    payload = response.json()
    missing = {"access_token", "refresh_token", "expires_at", "athlete"} - payload.keys()
    if missing:
        raise StravaError(f"token response missing fields: {sorted(missing)}")
    return payload
