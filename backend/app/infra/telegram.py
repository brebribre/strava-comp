"""Telegram Bot API client.

Only what the notifier needs: identify the bot, send text, send a photo with a caption.
"""

import logging
from typing import Any

import httpx

from app.config import get_settings

API_BASE = "https://api.telegram.org"
TIMEOUT = httpx.Timeout(20.0)
# Telegram truncates captions beyond this.
CAPTION_LIMIT = 1024

logger = logging.getLogger(__name__)


class TelegramError(RuntimeError):
    """Telegram rejected the request or could not be reached."""


class TelegramNotConfigured(TelegramError):
    """No bot token is set, so nothing can be sent."""


def _url(method: str) -> str:
    token = get_settings().telegram_bot_token
    if not token:
        raise TelegramNotConfigured("TELEGRAM_BOT_TOKEN is not set")
    return f"{API_BASE}/bot{token}/{method}"


def _unwrap(response: httpx.Response, method: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        raise TelegramError(f"{method}: unreadable response ({response.status_code})") from None

    if not payload.get("ok"):
        # description is Telegram's human-readable reason, e.g. "chat not found".
        raise TelegramError(f"{method}: {payload.get('description', 'unknown error')}")
    return payload["result"]


def get_me() -> dict[str, Any]:
    """Identify the bot — used to validate the token without sending anything."""
    try:
        response = httpx.get(_url("getMe"), timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise TelegramError(f"could not reach Telegram: {exc}") from exc
    return _unwrap(response, "getMe")


def send_message(chat_id: int, text: str) -> dict[str, Any]:
    try:
        response = httpx.post(
            _url("sendMessage"),
            data={"chat_id": chat_id, "text": text},
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise TelegramError(f"could not reach Telegram: {exc}") from exc
    return _unwrap(response, "sendMessage")


def send_photo(chat_id: int, image: bytes, caption: str, filename: str = "activity.png") -> dict[str, Any]:
    """Upload a photo with a caption. Multipart, so no public URL is needed."""
    try:
        response = httpx.post(
            _url("sendPhoto"),
            data={"chat_id": chat_id, "caption": caption[:CAPTION_LIMIT]},
            files={"photo": (filename, image, "image/png")},
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise TelegramError(f"could not reach Telegram: {exc}") from exc
    return _unwrap(response, "sendPhoto")
