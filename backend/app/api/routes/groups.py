from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAthlete, DbSession, MemberGroup
from app.schemas.groups import GroupCreate, GroupJoin, GroupMember, GroupRead
from app.schemas.feed import GroupFeed
from app.schemas.summary import GroupSummary, GroupTrend
from app.schemas.target import TargetProgress, TargetRead, TargetWrite
from app.services import groups as groups_service
from app.services import summary as summary_service
from app.services import target as target_service
from app.services.errors import GroupNotFound

router = APIRouter(prefix="/groups", tags=["groups"])


def _to_read(group, count: int) -> GroupRead:
    return GroupRead(
        id=group.id,
        name=group.name,
        invite_code=group.invite_code,
        created_by=group.created_by,
        created_at=group.created_at,
        member_count=count,
    )


@router.post(
    "",
    summary="Create a group",
    description="Creates a group with a random invite code and adds you as its first member.",
    response_model=GroupRead,
    status_code=status.HTTP_201_CREATED,
)
def create_group(body: GroupCreate, athlete: CurrentAthlete, session: DbSession) -> GroupRead:
    group = groups_service.create_group(session, body.name.strip(), athlete.athlete_id)
    return _to_read(group, groups_service.member_count(session, group.id))


@router.post(
    "/join",
    summary="Join a group by invite code",
    description="Idempotent — joining a group you are already in returns the group unchanged.",
    response_model=GroupRead,
)
def join_group(body: GroupJoin, athlete: CurrentAthlete, session: DbSession) -> GroupRead:
    try:
        group = groups_service.join_group(session, body.invite_code.strip(), athlete.athlete_id)
    except GroupNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No group with that invite code"
        ) from None
    return _to_read(group, groups_service.member_count(session, group.id))


@router.get(
    "",
    summary="List your groups",
    response_model=list[GroupRead],
)
def list_groups(athlete: CurrentAthlete, session: DbSession) -> list[GroupRead]:
    return [
        _to_read(group, count)
        for group, count in groups_service.list_groups_for_athlete(session, athlete.athlete_id)
    ]


@router.get(
    "/{group_id}/members",
    summary="List group members",
    description="Members only — 403 if you don't belong to the group, 404 if it doesn't exist.",
    response_model=list[GroupMember],
)
def list_members(group: MemberGroup, session: DbSession) -> list[GroupMember]:
    return [
        GroupMember(athlete_id=athlete.athlete_id, name=athlete.name, joined_at=membership.joined_at)
        for athlete, membership in groups_service.list_members(session, group.id)
    ]


DAYS_QUERY = Query(
    default=30,
    ge=1,
    le=365,
    description="Window size in days. Defaults to 30; BACKFILL_DAYS bounds how much history exists.",
)


@router.get(
    "/{group_id}/summary",
    summary="Activity summary for every group member",
    description=(
        "Totals per member and per sport over the window. Members with no activities are "
        "included with zeroes, and members are ordered by moving time (most active first). "
        "Members only."
    ),
    response_model=GroupSummary,
)
def group_summary(group: MemberGroup, session: DbSession, days: int = DAYS_QUERY) -> GroupSummary:
    return summary_service.group_summary(session, group, days)


@router.get(
    "/{group_id}/trend",
    summary="Weekly activity trend per member",
    description="Same window, bucketed by week — for a comparison chart across members. Members only.",
    response_model=GroupTrend,
)
def group_trend(group: MemberGroup, session: DbSession, days: int = DAYS_QUERY) -> GroupTrend:
    return summary_service.group_trend(session, group, days)


@router.get(
    "/{group_id}/feed",
    summary="Group activity feed",
    description=(
        "Every member's activities, newest first — the group's shared timeline. Paginate by "
        "passing the previous response's `next_before` back as `?before=`; a null `next_before` "
        "means there is nothing older. Members only."
    ),
    response_model=GroupFeed,
)
def group_feed(
    group: MemberGroup,
    session: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
    before: datetime | None = Query(default=None, description="Return activities started before this timestamp."),
) -> GroupFeed:
    return summary_service.group_feed(session, group, limit=limit, before=before)


@router.get(
    "/{group_id}/target",
    summary="Get the group's target",
    description="404 when the group has no target set yet. Members only.",
    response_model=TargetRead,
)
def get_target(group: MemberGroup, session: DbSession) -> TargetRead:
    target = target_service.get_target(session, group.id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No target set")
    return target_service.to_read(target)


@router.put(
    "/{group_id}/target",
    summary="Set or replace the group's target",
    description=(
        "A group has at most one target, so this replaces any existing one. Any member may "
        "set it — the group decides together."
    ),
    response_model=TargetRead,
)
def put_target(body: TargetWrite, group: MemberGroup, session: DbSession) -> TargetRead:
    return target_service.to_read(target_service.upsert_target(session, group.id, body))


@router.delete(
    "/{group_id}/target",
    summary="Remove the group's target",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_target(group: MemberGroup, session: DbSession) -> None:
    if not target_service.delete_target(session, group.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No target set")


@router.get(
    "/{group_id}/target/progress",
    summary="How every member is tracking against the target",
    description=(
        "Counts qualifying activities in the *current* period for every member, ordered "
        "furthest-ahead first. 404 when no target is set."
    ),
    response_model=TargetProgress,
)
def target_progress(group: MemberGroup, session: DbSession) -> TargetProgress:
    try:
        return target_service.target_progress(session, group)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No target set") from None
