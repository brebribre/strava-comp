"""Sending an encrypted push message to one browser.

Thin wrapper over pywebpush so the service layer never touches VAPID or encryption, and
so the two outcomes that matter — "gone, forget this device" and "failed, keep it" — are
expressed as a return value rather than an exception zoo.
"""

import json
import logging
from dataclasses import dataclass

from pywebpush import WebPushException, webpush

from app.config import get_settings

logger = logging.getLogger(__name__)

# The push service says the subscription is dead with one of these. Anything else (a
# timeout, a 500 on their side) is worth keeping the device for.
GONE_STATUSES = {404, 410}


@dataclass(frozen=True)
class Delivery:
    ok: bool
    # True only when the subscription itself is dead and should be deleted.
    gone: bool = False
    detail: str = ""


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.vapid_private_key and settings.vapid_public_key)


def send(endpoint: str, p256dh: str, auth: str, payload: dict) -> Delivery:
    """Encrypt and deliver one notification. Never raises."""
    if not is_configured():
        return Delivery(ok=False, detail="push is not configured on this server")

    settings = get_settings()
    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            # Apple holds a notification for a while if the device is asleep; a day is
            # long enough to survive a night and short enough that nobody is told about a
            # workout from last week.
            ttl=86_400,
        )
        return Delivery(ok=True)
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in GONE_STATUSES:
            return Delivery(ok=False, gone=True, detail=f"subscription gone ({status})")
        logger.warning("push to %s failed: %s", endpoint[:40], exc)
        return Delivery(ok=False, detail=str(exc)[:200])
    except Exception as exc:  # noqa: BLE001 - a notification must never break a request
        logger.exception("unexpected push failure")
        return Delivery(ok=False, detail=str(exc)[:200])
