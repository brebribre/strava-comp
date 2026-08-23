import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import CurrentAthlete, DbSession
from app.config import get_settings
from app.infra.strava import StravaError, build_authorize_url
from app.schemas.auth import AthleteMe, LogoutResponse
from app.services import auth as auth_service
from app.services.session import create_oauth_state, create_session_token, read_oauth_state

router = APIRouter(tags=["auth"])

settings = get_settings()

# Short-lived cookie holding the CSRF nonce that must match Strava's `state` echo.
_STATE_COOKIE = "sgt_oauth_state"
_STATE_MAX_AGE = 600


def _set_session_cookie(response: Response, athlete_id: int) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(athlete_id),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",  # lax still sends the cookie on the top-level redirect back from Strava
        path="/",
    )


def _frontend_redirect(**params: str) -> RedirectResponse:
    url = settings.frontend_origin
    if params:
        url = f"{url}?{urlencode(params)}"
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


@router.get(
    "/auth/strava/login",
    summary="Start Strava login",
    description="Redirects to Strava's consent screen. Open this in a browser — it is not a JSON endpoint.",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={307: {"description": "Redirect to Strava's OAuth consent screen"}},
)
def strava_login() -> RedirectResponse:
    if not settings.strava_client_id or not settings.strava_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET are not configured",
        )

    nonce = secrets.token_urlsafe(16)
    response = RedirectResponse(url=build_authorize_url(create_oauth_state(nonce)))
    response.set_cookie(
        key=_STATE_COOKIE,
        value=nonce,
        max_age=_STATE_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@router.get(
    "/auth/strava/callback",
    summary="Strava OAuth callback",
    description=(
        "Strava redirects here with `code`, `scope` and `state`. Exchanges the code for "
        "tokens, upserts the athlete, sets the session cookie, then redirects to the frontend."
    ),
    include_in_schema=True,
    responses={303: {"description": "Redirect to the frontend, logged in or with an `error` param"}},
)
def strava_callback(
    request: Request,
    session: DbSession,
    code: str | None = None,
    state: str | None = None,
    scope: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    # The user hit "Cancel" on Strava's consent screen.
    if error:
        return _frontend_redirect(error=error)

    if not code or not state:
        return _frontend_redirect(error="missing_code")

    # CSRF: the signed state must decode, and its nonce must match our cookie.
    expected_nonce = request.cookies.get(_STATE_COOKIE)
    nonce = read_oauth_state(state, max_age_seconds=_STATE_MAX_AGE)
    if not expected_nonce or nonce is None or not secrets.compare_digest(nonce, expected_nonce):
        return _frontend_redirect(error="invalid_state")

    # Without activity:read_all we can only see public activities — worth surfacing.
    granted = set((scope or "").split(","))
    if "activity:read_all" not in granted:
        return _frontend_redirect(error="insufficient_scope")

    try:
        athlete = auth_service.login_with_code(session, code)
    except StravaError:
        return _frontend_redirect(error="strava_exchange_failed")

    response = _frontend_redirect(login="ok")
    _set_session_cookie(response, athlete.athlete_id)
    response.delete_cookie(_STATE_COOKIE, path="/")
    return response


@router.get("/me", summary="Current athlete", response_model=AthleteMe)
def me(athlete: CurrentAthlete) -> AthleteMe:
    return AthleteMe(
        athlete_id=athlete.athlete_id, name=athlete.name, created_at=athlete.created_at
    )


@router.post("/auth/logout", summary="Log out", response_model=LogoutResponse)
def logout(response: Response) -> LogoutResponse:
    response.delete_cookie(settings.session_cookie_name, path="/")
    return LogoutResponse(status="logged_out")
