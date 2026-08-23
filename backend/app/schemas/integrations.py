from pydantic import BaseModel


class TelegramSettings(BaseModel):
    """A group's Telegram wiring, as the setup screen needs it."""

    is_configured: bool = False
    # Shown so people can confirm they connected the chat they meant to.
    chat_title: str | None = None
    # The code to send as "/connect <code>" in the chat.
    pairing_code: str | None = None
    bot_username: str | None = None


class TelegramTestResult(BaseModel):
    sent: bool
    detail: str
