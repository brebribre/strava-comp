"""Web push: what the browser needs to subscribe, and where it says it has."""

from fastapi import APIRouter, Header, HTTPException, status

from app.api.deps import CurrentAthlete, DbSession
from app.config import get_settings
from app.infra import webpush
from app.schemas.push import (
    PushConfig,
    PushSubscriptionRead,
    PushSubscriptionWrite,
    PushTestResult,
)
from app.services import push

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/config", response_model=PushConfig, summary="The key a browser subscribes with")
def push_config() -> PushConfig:
    """Public — the application server key is not a secret, and the login page has no session."""
    settings = get_settings()
    return PushConfig(
        public_key=settings.vapid_public_key,
        enabled=webpush.is_configured(),
    )


@router.get(
    "/subscriptions",
    response_model=list[PushSubscriptionRead],
    summary="Devices currently subscribed",
)
def list_subscriptions(session: DbSession, athlete: CurrentAthlete) -> list[PushSubscriptionRead]:
    return [
        PushSubscriptionRead(
            endpoint=row.endpoint,
            user_agent=row.user_agent,
            created_at=row.created_at,
            last_used_at=row.last_used_at,
        )
        for row in push.subscriptions_for(session, athlete.athlete_id)
    ]


@router.post(
    "/subscriptions",
    response_model=PushSubscriptionRead,
    summary="Subscribe this device",
)
def subscribe(
    body: PushSubscriptionWrite,
    session: DbSession,
    athlete: CurrentAthlete,
    user_agent: str | None = Header(default=None),
) -> PushSubscriptionRead:
    if not webpush.is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "push is not configured on this server"
        )
    row = push.save_subscription(session, athlete.athlete_id, body, user_agent)
    return PushSubscriptionRead(
        endpoint=row.endpoint,
        user_agent=row.user_agent,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
    )


@router.delete(
    "/subscriptions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unsubscribe this device",
)
def unsubscribe(body: PushSubscriptionWrite, session: DbSession, athlete: CurrentAthlete) -> None:
    if not push.delete_subscription(session, athlete.athlete_id, body.endpoint):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such subscription")


@router.post(
    "/test",
    response_model=PushTestResult,
    summary="Send yourself a test notification",
)
def send_test(session: DbSession, athlete: CurrentAthlete) -> PushTestResult:
    """The only way to know a phone is really set up is to make it buzz."""
    delivered = push.send_to_athletes(
        session,
        [athlete.athlete_id],
        {
            "title": "Bruderbande",
            "body": "Notifications are working on this device.",
            "url": "/recap",
        },
    )
    return PushTestResult(
        delivered=delivered,
        detail="sent" if delivered else "no device is subscribed on this account",
    )
