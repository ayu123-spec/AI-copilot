"""The Notifier fans a notification out to one or more channels, skipping any
below the configured severity threshold and never letting a channel failure
break the caller."""

import logging

from app.notifications.base import LEVELS, Notification, NotificationChannel

logger = logging.getLogger("cortex.notifications")


class Notifier:
    def __init__(
        self, channels: list[NotificationChannel], min_level: str = "info"
    ) -> None:
        self.channels = channels
        self.min_level = LEVELS.get(min_level, 0)

    def notify(self, notification: Notification) -> bool:
        if LEVELS.get(notification.level, 0) < self.min_level:
            return False
        delivered = True
        for channel in self.channels:
            try:
                delivered = channel.send(notification) and delivered
            except Exception:  # pragma: no cover - a bad channel must not 500
                logger.exception("notification channel failed")
                delivered = False
        return delivered
