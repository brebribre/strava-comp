from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentAthlete, DbSession, MemberGroup
from app.schemas.groups import GroupCreate, GroupJoin, GroupMember, GroupRead
from app.services import groups as groups_service
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
