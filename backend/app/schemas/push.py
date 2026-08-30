from datetime import datetime

from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    """The browser's half of the encryption, exactly as PushSubscription.toJSON() gives it."""

    p256dh: str
    auth: str


class PushSubscriptionWrite(BaseModel):
    endpoint: str = Field(min_length=1, max_length=2000)
    keys: PushKeys


class PushSubscriptionRead(BaseModel):
    endpoint: str
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime | None


class PushConfig(BaseModel):
    """What the browser needs before it can subscribe."""

    # Empty when the server has no keys, which is how the UI knows to stay quiet rather
    # than offering a button that cannot work.
    public_key: str
    enabled: bool


class PushTestResult(BaseModel):
    delivered: int
    detail: str
