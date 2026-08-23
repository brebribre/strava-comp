"""Point the Telegram bot at this deployment's webhook.

    .venv/bin/python -m scripts.setup_telegram_webhook https://api.bruderbande.com
    .venv/bin/python -m scripts.setup_telegram_webhook --info
    .venv/bin/python -m scripts.setup_telegram_webhook --delete

Run once per environment. Telegram allows a single webhook URL per bot, so pointing it at
production means local /connect commands stop arriving (use --delete plus polling locally).
"""

import sys

import httpx

from app.config import get_settings

settings = get_settings()


def _api(method: str) -> str:
    if not settings.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN is not set")
        sys.exit(1)
    return f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"


def show() -> None:
    info = httpx.get(_api("getWebhookInfo"), timeout=15).json().get("result", {})
    print("current webhook:")
    for key in ("url", "pending_update_count", "last_error_message", "last_error_date"):
        if info.get(key):
            print(f"  {key}: {info[key]}")
    if not info.get("url"):
        print("  (none set)")


def set_webhook(base_url: str) -> None:
    url = f"{base_url.rstrip('/')}/telegram/webhook"
    response = httpx.post(
        _api("setWebhook"),
        data={
            "url": url,
            "secret_token": settings.telegram_webhook_secret,
            # Only these matter; skip the firehose of edits, reactions and polls.
            "allowed_updates": '["message", "channel_post", "my_chat_member"]',
            "drop_pending_updates": "true",
        },
        timeout=15,
    ).json()
    print(f"setWebhook -> {response.get('ok')}: {response.get('description')}")
    print(f"  url: {url}")


def delete() -> None:
    response = httpx.post(_api("deleteWebhook"), data={"drop_pending_updates": "true"}, timeout=15).json()
    print(f"deleteWebhook -> {response.get('ok')}: {response.get('description')}")


if __name__ == "__main__":
    if "--info" in sys.argv:
        show()
    elif "--delete" in sys.argv:
        delete()
    elif len(sys.argv) > 1:
        set_webhook(sys.argv[1])
        show()
    else:
        print(__doc__)
