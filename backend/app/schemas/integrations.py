from pydantic import BaseModel, Field


class TelegramSettings(BaseModel):
    """A group's Telegram wiring. `null` chat id means notifications are off."""

    telegram_chat_id: int | None = None
    is_configured: bool = False
    bot_username: str | None = None


class TelegramWrite(BaseModel):
    # Group chats are negative and can exceed int32, hence a plain int with no bounds.
    telegram_chat_id: int | None = Field(
        default=None, description="Telegram chat id, e.g. -1001234567890. Null disables."
    )


class TelegramTestResult(BaseModel):
    sent: bool
    detail: str
