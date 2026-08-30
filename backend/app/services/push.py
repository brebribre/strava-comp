"""Push subscriptions and the notifications sent to them."""

import logging

from sqlmodel import Session, select

from app.infra import webpush
from app.models import Activity, Athlete, Group, GroupMembership, PushSubscription
from app.models.base import utcnow
from app.schemas.push import PushSubscriptionWrite

logger = logging.getLogger(__name__)


def save_subscription(
    session: Session, athlete_id: int, data: PushSubscriptionWrite, user_agent: str | None
) -> PushSubscription:
    """Store a device's subscription, or refresh it if we have seen this endpoint before.

    The endpoint is the primary key, so re-subscribing on the same phone updates the keys
    rather than piling up rows — which matters because a browser silently re-subscribes
    whenever its keys rotate.
    """
    existing = session.get(PushSubscription, data.endpoint)
    if existing is not None:
        existing.athlete_id = athlete_id
        existing.p256dh = data.keys.p256dh
        existing.auth = data.keys.auth
        existing.user_agent = user_agent
        subscription = existing
    else:
        subscription = PushSubscription(
            endpoint=data.endpoint,
            athlete_id=athlete_id,
            p256dh=data.keys.p256dh,
            auth=data.keys.auth,
            user_agent=user_agent,
        )

    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    return subscription


def delete_subscription(session: Session, athlete_id: int, endpoint: str) -> bool:
    """Forget one device. Scoped to the athlete so nobody can unsubscribe someone else."""
    subscription = session.get(PushSubscription, endpoint)
    if subscription is None or subscription.athlete_id != athlete_id:
        return False
    session.delete(subscription)
    session.commit()
    return True


def subscriptions_for(session: Session, athlete_id: int) -> list[PushSubscription]:
    return list(
        session.exec(
            select(PushSubscription).where(PushSubscription.athlete_id == athlete_id)
        ).all()
    )


def send_to_athletes(session: Session, athlete_ids: list[int], payload: dict) -> int:
    """Deliver one notification to every device of every listed athlete.

    Returns how many devices took it. Subscriptions the push service reports as gone are
    deleted here: a phone that was reset or a web app that was removed from the home
    screen would otherwise fail forever.
    """
    if not athlete_ids or not webpush.is_configured():
        return 0

    devices = list(
        session.exec(
            select(PushSubscription).where(PushSubscription.athlete_id.in_(athlete_ids))
        ).all()
    )

    delivered = 0
    for device in devices:
        result = webpush.send(device.endpoint, device.p256dh, device.auth, payload)
        if result.ok:
            device.last_used_at = utcnow()
            session.add(device)
            delivered += 1
        elif result.gone:
            logger.info("dropping dead subscription for athlete %s", device.athlete_id)
            session.delete(device)

    session.commit()
    return delivered


def audience_for_activity(session: Session, activity: Activity) -> list[int]:
    """Everyone who should hear about this activity: every member of every group the
    athlete belongs to, the athlete included.

    Including the athlete is deliberate — seeing your own workout land is how you know the
    thing works at all, and it confirms Strava actually delivered it.
    """
    rows = session.exec(
        select(GroupMembership.athlete_id)
        .join(Group, Group.id == GroupMembership.group_id)
        .where(
            GroupMembership.group_id.in_(
                select(GroupMembership.group_id).where(
                    GroupMembership.athlete_id == activity.owner_id
                )
            )
        )
    ).all()
    return sorted({athlete_id for athlete_id in rows})


def notify_activity(session: Session, activity_id: int) -> int:
    """Push one finished activity to everyone who shares a group with its owner."""
    activity = session.get(Activity, activity_id)
    if activity is None:
        return 0
    athlete = session.get(Athlete, activity.owner_id)
    if athlete is None:
        return 0

    what = activity.name or activity.sport_type or "an activity"
    payload = {
        "title": f"{athlete.name} just finished a workout",
        "body": what,
        "activity_id": activity.id,
        # Where the notification takes you when tapped. A group is picked below.
        "url": _activity_url(session, activity),
    }
    return send_to_athletes(session, audience_for_activity(session, activity), payload)


def _activity_url(session: Session, activity: Activity) -> str:
    """Deep link for the notification: the activity inside one of the owner's groups."""
    group_id = session.exec(
        select(GroupMembership.group_id)
        .where(GroupMembership.athlete_id == activity.owner_id)
        .order_by(GroupMembership.joined_at)
        .limit(1)
    ).first()
    return f"/groups/{group_id}/activities/{activity.id}" if group_id else "/recap"
