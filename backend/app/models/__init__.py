"""SQLModel table definitions.

Every model must be imported here so SQLModel.metadata sees it at table-create time
(see app/infra/db.py).
"""

from app.models.activity import Activity
from app.models.athlete import Athlete
from app.models.group import Group, GroupMembership
from app.models.integration import ActivityNotification, GroupIntegration
from app.models.push import PushSubscription
from app.models.target import GroupTarget

__all__ = [
    "Activity",
    "ActivityNotification",
    "Athlete",
    "Group",
    "GroupIntegration",
    "GroupMembership",
    "GroupTarget",
    "PushSubscription",
]
