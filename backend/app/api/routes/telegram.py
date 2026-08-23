import hmac
import logging

from fastapi import APIRouter, Header, Request, status
from sqlmodel import Session

from app.api.deps import DbSession
from app.config import get_settings
from app.infra import telegram
from app.services import notifications

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)
settings = get_settings()

HELP = (
    "Bruderbande posts your group's activities here.\n\n"
    "To connect: open your group's Settings in the app, copy the code, then send:\n"
    "/connect YOURCODE"
)


def _reply(chat_id: int, text: str) -> None:
    """Replies are best-effort: a failure here must not make us retry the whole update."""
    try:
        telegram.send_message(chat_id, text)
    except telegram.TelegramError as exc:
        logger.warning("could not reply in chat %s: %s", chat_id, exc)


def _handle_command(session: Session, chat_id: int, chat_title: str | None, text: str) -> None:
    # In groups, commands arrive addressed to the bot: "/connect@BruderBandeBot ABC123".
    parts = text.strip().split()
    command = parts[0].split("@")[0].lower()
    argument = parts[1] if len(parts) > 1 else ""

    if command in ("/start", "/help"):
        _reply(chat_id, HELP)
        return

    if command == "/connect":
        if not argument:
            _reply(chat_id, "Send the code from the app, like:\n/connect ABC123")
            return
        group = notifications.connect_by_code(session, argument, chat_id, chat_title)
        if group is None:
            _reply(chat_id, "That code didn't match any group. Check the app for the current one.")
            return
        _reply(chat_id, f"Connected to {group.name}. Activities will show up here.")
        logger.info("chat %s connected to group %s", chat_id, group.id)
        return

    if command == "/disconnect":
        group = notifications.disconnect_chat(session, chat_id)
        _reply(
            chat_id,
            f"Disconnected from {group.name}." if group else "This chat isn't connected to a group.",
        )
        return


@router.post(
    "/webhook",
    summary="Telegram bot updates",
    description=(
        "Receives bot updates. Verified with the secret token Telegram echoes in "
        "`X-Telegram-Bot-Api-Secret-Token`. Always returns 200 so Telegram doesn't retry."
    ),
    status_code=status.HTTP_200_OK,
)
async def telegram_webhook(
    request: Request,
    session: DbSession,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if not hmac.compare_digest(
        x_telegram_bot_api_secret_token or "", settings.telegram_webhook_secret
    ):
        logger.warning("telegram webhook: bad secret token")
        # Still a 200: a 4xx makes Telegram retry, and this is never going to succeed.
        return {"status": "ignored"}

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        return {"status": "ignored"}

    message = payload.get("message") or payload.get("channel_post") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = message.get("text") or ""

    if chat_id is None or not text.startswith("/"):
        return {"status": "ignored"}

    try:
        _handle_command(session, chat_id, chat.get("title"), text)
    except Exception:  # noqa: BLE001 - never hand Telegram a reason to retry
        logger.exception("telegram webhook: failed handling %r", text[:40])

    return {"status": "ok"}
