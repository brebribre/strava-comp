"""HTTP client for the Strava API.

Filled in from Phase 3 onwards: OAuth token exchange/refresh, activity fetching,
and webhook subscription management all live here. Keeping every outbound Strava
call in one module means services never touch httpx directly.
"""

STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_OAUTH_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_OAUTH_TOKEN_URL = "https://www.strava.com/oauth/token"
