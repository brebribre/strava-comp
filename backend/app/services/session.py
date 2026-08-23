"""Signed session cookies.

The cookie carries only the athlete ID, signed and timestamped with itsdangerous —
no server-side session store, and nothing sensitive in the payload.
"""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

_SESSION_SALT = "session"
_OAUTH_STATE_SALT = "oauth-state"


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=salt)


def create_session_token(athlete_id: int) -> str:
    return _serializer(_SESSION_SALT).dumps({"athlete_id": athlete_id})


def read_session_token(token: str) -> int | None:
    """Return the athlete ID, or None if the token is invalid, tampered or expired."""
    try:
        data = _serializer(_SESSION_SALT).loads(
            token, max_age=get_settings().session_max_age_seconds
        )
    except (BadSignature, SignatureExpired):
        return None
    athlete_id = data.get("athlete_id") if isinstance(data, dict) else None
    return athlete_id if isinstance(athlete_id, int) else None


def create_oauth_state(nonce: str, invite_code: str | None = None) -> str:
    """Sign the CSRF nonce that round-trips through Strava as `state`.

    An invite code rides along so a logged-out visitor following an invite link is joined
    to the group after authorizing. It's signed, so it can't be swapped for another
    group's code en route.
    """
    payload: dict[str, str] = {"nonce": nonce}
    if invite_code:
        payload["invite"] = invite_code
    return _serializer(_OAUTH_STATE_SALT).dumps(payload)


def read_oauth_state(state: str, max_age_seconds: int = 600) -> dict[str, str] | None:
    """Return the decoded state payload, or None if invalid/tampered/expired."""
    try:
        data = _serializer(_OAUTH_STATE_SALT).loads(state, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("nonce"), str):
        return None
    return data
