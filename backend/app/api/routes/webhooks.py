import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas.webhooks import WebhookEvent
from app.services import webhooks as webhooks_service

router = APIRouter(prefix="/strava", tags=["strava"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.get(
    "/webhook",
    summary="Webhook subscription validation",
    description=(
        "Strava calls this once when a push subscription is created. It must echo back "
        "`hub.challenge` within a couple of seconds, and only if `hub.verify_token` matches."
    ),
)
def verify_subscription(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
) -> JSONResponse:
    # compare_digest keeps the comparison constant-time.
    if not hmac.compare_digest(hub_verify_token, settings.strava_verify_token):
        logger.warning("webhook verification rejected: verify_token mismatch")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid verify token")
    if hub_mode != "subscribe":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unexpected hub.mode")

    # The key really is literally "hub.challenge".
    return JSONResponse({"hub.challenge": hub_challenge})


@router.post(
    "/webhook",
    summary="Receive a Strava event",
    description=(
        "Acknowledged immediately with 200; the work happens in a background task. "
        "Strava requires an ack within 2 seconds and retries very little."
    ),
    status_code=status.HTTP_200_OK,
)
async def receive_event(request: Request, background: BackgroundTasks) -> dict:
    # Parse defensively: a malformed payload must still be acked, or Strava may
    # disable the subscription.
    try:
        payload = await request.json()
        event = WebhookEvent.model_validate(payload)
    except Exception:  # noqa: BLE001
        logger.warning("webhook: unparseable payload, acking anyway")
        return {"status": "ignored"}

    background.add_task(
        webhooks_service.process_event,
        event.object_type,
        event.object_id,
        event.aspect_type,
        event.owner_id,
        event.updates,
    )
    return {"status": "accepted"}
