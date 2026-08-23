from typing import Any

from pydantic import BaseModel, Field


class WebhookEvent(BaseModel):
    """A Strava push-subscription event.

    https://developers.strava.com/docs/webhooks/
    """

    object_type: str  # "activity" | "athlete"
    object_id: int  # activity id, or athlete id for athlete events
    aspect_type: str  # "create" | "update" | "delete"
    owner_id: int  # athlete who owns the object
    subscription_id: int
    event_time: int
    updates: dict[str, Any] = Field(default_factory=dict)


class WebhookChallenge(BaseModel):
    """Strava's subscription validation handshake response."""

    hub_challenge: str = Field(serialization_alias="hub.challenge")

    model_config = {"populate_by_name": True}
