"""Announcing finished activities to a group's Telegram chat."""

import logging
import secrets
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.infra import telegram
from app.infra.db import engine
from app.models import (
    Activity,
    ActivityNotification,
    Athlete,
    Group,
    GroupIntegration,
    GroupMembership,
    GroupTarget,
)
from app.models.base import utcnow
from app.schemas.target import TargetRules
from app.services.share_card import render_activity_card
from app.services.target import count_exercises, local_start, qualifies

logger = logging.getLogger(__name__)


def get_integration(session: Session, group_id: int) -> GroupIntegration | None:
    return session.get(GroupIntegration, group_id)


def _integration(session: Session, group_id: int) -> GroupIntegration:
    integration = session.get(GroupIntegration, group_id)
    if integration is None:
        integration = GroupIntegration(group_id=group_id)
        session.add(integration)
        session.commit()
        session.refresh(integration)
    return integration


def set_telegram_chat(
    session: Session,
    group_id: int,
    chat_id: int | None,
    chat_title: str | None = None,
) -> GroupIntegration:
    integration = _integration(session, group_id)
    integration.telegram_chat_id = chat_id
    integration.telegram_chat_title = chat_title if chat_id is not None else None
    integration.updated_at = utcnow()
    session.add(integration)
    session.commit()
    session.refresh(integration)
    return integration


# Characters that survive being read aloud and retyped: no O/0, I/1, etc.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 6


def issue_pairing_code(session: Session, group_id: int) -> str:
    """Mint (or reuse) the code the user types into their Telegram chat."""
    integration = _integration(session, group_id)
    if not integration.pairing_code:
        integration.pairing_code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
        integration.updated_at = utcnow()
        session.add(integration)
        session.commit()
        session.refresh(integration)
    return integration.pairing_code


def connect_by_code(
    session: Session, code: str, chat_id: int, chat_title: str | None
) -> Group | None:
    """Link a Telegram chat to whichever group owns this pairing code.

    Returns the group, or None if the code is unknown. The code is rotated on success so a
    forwarded message can't be replayed to hijack the connection later.
    """
    integration = session.exec(
        select(GroupIntegration).where(GroupIntegration.pairing_code == code.strip().upper())
    ).first()
    if integration is None:
        return None

    integration.telegram_chat_id = chat_id
    integration.telegram_chat_title = chat_title
    integration.pairing_code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
    integration.updated_at = utcnow()
    session.add(integration)
    session.commit()

    return session.get(Group, integration.group_id)


def disconnect_chat(session: Session, chat_id: int) -> Group | None:
    """Unlink whichever group is bound to this chat — used by /disconnect in Telegram."""
    integration = session.exec(
        select(GroupIntegration).where(GroupIntegration.telegram_chat_id == chat_id)
    ).first()
    if integration is None:
        return None
    integration.telegram_chat_id = None
    integration.telegram_chat_title = None
    integration.updated_at = utcnow()
    session.add(integration)
    session.commit()
    return session.get(Group, integration.group_id)


def caption_for(activity: Activity, athlete: Athlete) -> str:
    what = activity.name or activity.sport_type or "an activity"
    return f"{athlete.name} just did {what}!"


def _should_announce(session: Session, group: Group, activity: Activity) -> bool:
    """Qualification is the group's own bar; with no target set, everything counts.

    A short session that on its own clears nothing still gets announced when it is the one
    that tips the day over the bar — otherwise the group would see a target tick up with no
    message explaining it.
    """
    target = session.get(GroupTarget, group.id)
    if target is None:
        return True

    rules = TargetRules.model_validate(target.rules)
    if qualifies(activity, rules):
        return True

    # Does the day count for more with this activity in it than without?
    same_day = _same_local_day(session, activity)
    without = [other for other in same_day if other.id != activity.id]
    return count_exercises(same_day, rules) > count_exercises(without, rules)


def _same_local_day(session: Session, activity: Activity) -> list[Activity]:
    """The athlete's other activities on the same local day, this one included.

    The window is a day either side in UTC, then narrowed on the local date, which is what
    makes this correct for an athlete whose local day straddles the UTC one.
    """
    if activity.start_date is None:
        return [activity]

    nearby = session.exec(
        select(Activity).where(
            Activity.owner_id == activity.owner_id,
            Activity.start_date >= activity.start_date - timedelta(days=1),
            Activity.start_date <= activity.start_date + timedelta(days=1),
        )
    ).all()

    day = local_start(activity).date()
    return [other for other in nearby if local_start(other).date() == day]


def _already_sent(session: Session, activity_id: int, group_id: int) -> bool:
    return session.get(ActivityNotification, (activity_id, group_id)) is not None


def _mark_sent(session: Session, activity_id: int, group_id: int) -> bool:
    """Claim the (activity, group) pair. False if another worker got there first."""
    session.add(ActivityNotification(activity_id=activity_id, group_id=group_id))
    try:
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False


def announce_activity(session: Session, activity_id: int) -> int:
    """Post an activity to every eligible group chat. Returns how many were notified."""
    activity = session.get(Activity, activity_id)
    if activity is None:
        return 0
    athlete = session.get(Athlete, activity.owner_id)
    if athlete is None:
        return 0

    groups = session.exec(
        select(Group)
        .join(GroupMembership, GroupMembership.group_id == Group.id)
        .join(GroupIntegration, GroupIntegration.group_id == Group.id)
        .where(
            GroupMembership.athlete_id == activity.owner_id,
            GroupIntegration.telegram_chat_id.is_not(None),
        )
    ).all()

    sent = 0
    image: bytes | None = None
    for group in groups:
        if _already_sent(session, activity.id, group.id):
            continue
        if not _should_announce(session, group, activity):
            logger.info("activity %s does not qualify for group %s", activity.id, group.id)
            continue

        integration = session.get(GroupIntegration, group.id)
        chat_id = integration.telegram_chat_id if integration else None
        if chat_id is None:
            continue

        # Claim before sending: a duplicate post is worse than a missed one, and Strava
        # can deliver create and update within the same second.
        if not _mark_sent(session, activity.id, group.id):
            continue

        try:
            # Rendered once even when several groups share the athlete.
            if image is None:
                image = render_activity_card(activity, athlete)
            telegram.send_photo(chat_id, image, caption_for(activity, athlete))
            sent += 1
            logger.info("announced activity %s to group %s", activity.id, group.id)
        except telegram.TelegramError as exc:
            # Release the claim so a later retry can succeed.
            record = session.get(ActivityNotification, (activity.id, group.id))
            if record is not None:
                session.delete(record)
                session.commit()
            logger.warning("telegram send failed for group %s: %s", group.id, exc)

    return sent


def announce_in_background(activity_id: int) -> None:
    """BackgroundTasks entry point — owns its session, never raises."""
    try:
        with Session(engine) as session:
            announce_activity(session, activity_id)
    except Exception:  # noqa: BLE001 - a background task must not crash the worker
        logger.exception("unexpected failure announcing activity %s", activity_id)
