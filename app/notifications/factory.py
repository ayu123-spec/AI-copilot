"""Build the Notifier from configuration (NOTIFICATION_CHANNEL)."""

from functools import lru_cache

from app.core.config import settings
from app.notifications.channels import (
    ConsoleChannel,
    EmailChannel,
    InMemoryChannel,
    SlackWebhookChannel,
    TeamsWebhookChannel,
)
from app.notifications.notifier import Notifier


@lru_cache
def get_notifier() -> Notifier:
    backend = (settings.NOTIFICATION_CHANNEL or "console").lower()
    if backend == "memory":
        channel = InMemoryChannel()
    elif backend == "slack":  # pragma: no cover - network
        channel = SlackWebhookChannel(settings.SLACK_WEBHOOK_URL or "")
    elif backend == "teams":  # pragma: no cover - network
        channel = TeamsWebhookChannel(settings.TEAMS_WEBHOOK_URL or "")
    elif backend == "email":  # pragma: no cover - SMTP
        channel = EmailChannel(
            host=settings.SMTP_HOST or "",
            port=settings.SMTP_PORT,
            user=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            sender=settings.NOTIFICATION_EMAIL_FROM or (settings.SMTP_USER or ""),
            recipient=settings.NOTIFICATION_EMAIL_TO or "",
        )
    else:
        channel = ConsoleChannel()
    return Notifier([channel], min_level=settings.NOTIFICATION_MIN_LEVEL)
