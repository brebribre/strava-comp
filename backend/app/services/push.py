"""Push subscriptions and the notifications sent to them."""

import logging

from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.infra import webpush
from app.models import (
    Activity,
    Athlete,
    Group,
    GroupMembership,
    GroupTarget,
    PushDayNotification,
    PushSubscription,
)
from app.models.base import utcnow
from app.schemas.push import PushSubscriptionWrite
from app.schemas.target import TargetRules
from app.services.target import activities_on_local_day, count_exercises, local_start, started

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


def members_of(session: Session, group_id: int) -> list[int]:
    return list(
        session.exec(
            select(GroupMembership.athlete_id).where(GroupMembership.group_id == group_id)
        ).all()
    )


def groups_of(session: Session, athlete_id: int) -> list[Group]:
    return list(
        session.exec(
            select(Group)
            .join(GroupMembership, GroupMembership.group_id == Group.id)
            .where(GroupMembership.athlete_id == athlete_id)
        ).all()
    )


def _claim_day(session: Session, athlete_id: int, group_id: int, day: date) -> bool:
    """Claim today's notification for this athlete in this group. False if already sent.

    Claimed before sending, like the Telegram path: a second buzz is worse than a missed
    one, and Strava can deliver a create and an update within the same second.
    """
    session.add(PushDayNotification(athlete_id=athlete_id, group_id=group_id, local_day=day))
    try:
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False


def reached_today(session: Session, activity: Activity, target: GroupTarget) -> bool:
    """Has this athlete's day now cleared the group's bar?

    Asked of the whole day rather than of this activity, which is the point: twenty minutes
    followed by twenty-five is a day that qualifies even though neither half does. Whether
    this is the *first* time it qualifies is not asked here — the day claim answers that,
    and it does so even if we never saw the activity that would have crossed the line.
    """
    day = local_start(activity).date()
    rules = TargetRules.model_validate(target.rules)
    todays = [
        item
        for item in activities_on_local_day(session, activity.owner_id, day)
        if started(item, target)
    ]
    return count_exercises(todays, rules) >= 1


def notify_activity(session: Session, activity_id: int) -> int:
    """Tell the groups whose target this athlete has just reached today.

    Nothing is sent for an ordinary workout that leaves the day short of the bar, and
    nothing is sent twice in a day. A group with no target set has no bar to reach, so it
    stays quiet.
    """
    activity = session.get(Activity, activity_id)
    if activity is None or activity.start_date is None:
        return 0
    athlete = session.get(Athlete, activity.owner_id)
    if athlete is None:
        return 0

    day = local_start(activity).date()
    recipients: set[int] = set()

    for group in groups_of(session, athlete.athlete_id):
        target = session.get(GroupTarget, group.id)
        if target is None or not reached_today(session, activity, target):
            continue
        if not _claim_day(session, athlete.athlete_id, group.id, day):
            continue
        recipients.update(members_of(session, group.id))

    if not recipients:
        return 0

    minutes = sum(
        item.moving_time or 0 for item in activities_on_local_day(session, athlete.athlete_id, day)
    ) // 60
    what = activity.name or activity.sport_type or "an activity"

    return send_to_athletes(
        session,
        sorted(recipients),
        {
            "title": f"{athlete.name} has reached today's target!",
            "body": f"{what} · {minutes} min today",
            "activity_id": activity.id,
            "url": _activity_url(session, activity),
        },
    )


def _activity_url(session: Session, activity: Activity) -> str:
    """Deep link for the notification: the activity inside one of the owner's groups."""
    group_id = session.exec(
        select(GroupMembership.group_id)
        .where(GroupMembership.athlete_id == activity.owner_id)
        .order_by(GroupMembership.joined_at)
        .limit(1)
    ).first()
    return f"/groups/{group_id}/activities/{activity.id}" if group_id else "/recap"
