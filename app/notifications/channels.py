"""Notification delivery channels.

``InMemoryChannel`` and ``ConsoleChannel`` are dependency-free and safe in tests
and offline. The webhook + email channels make real network/SMTP calls and are
only used when configured (excluded from coverage).
"""

import json
import logging
import urllib.request

from app.notifications.base import Notification, NotificationChannel

logger = logging.getLogger("cortex.notifications")


class InMemoryChannel(NotificationChannel):
    """Collects notifications in a list — handy for tests and previews."""

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def send(self, notification: Notification) -> bool:
        self.sent.append(notification)
        return True


class ConsoleChannel(NotificationChannel):
    """Logs the notification. Safe everywhere; the sensible local default."""

    def send(self, notification: Notification) -> bool:
        logger.info(
            "[notify:%s] %s — %s",
            notification.level,
            notification.title,
            notification.body,
        )
        return True


def _post_json(url: str, payload: dict) -> bool:  # pragma: no cover - network
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return 200 <= resp.status < 300


class SlackWebhookChannel(NotificationChannel):  # pragma: no cover - network
    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    def send(self, notification: Notification) -> bool:
        if not self._url:
            return False
        text = f"*{notification.title}*\n{notification.body}"
        return _post_json(self._url, {"text": text})


class TeamsWebhookChannel(NotificationChannel):  # pragma: no cover - network
    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    def send(self, notification: Notification) -> bool:
        if not self._url:
            return False
        return _post_json(
            self._url,
            {"title": notification.title, "text": notification.body},
        )


class EmailChannel(NotificationChannel):  # pragma: no cover - SMTP
    def __init__(
        self,
        host: str,
        port: int,
        user: str | None,
        password: str | None,
        sender: str,
        recipient: str,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._sender = sender
        self._recipient = recipient

    def send(self, notification: Notification) -> bool:
        import smtplib
        from email.message import EmailMessage

        if not (self._host and self._recipient):
            return False
        msg = EmailMessage()
        msg["Subject"] = notification.title
        msg["From"] = self._sender
        msg["To"] = self._recipient
        msg.set_content(notification.body or notification.title)
        with smtplib.SMTP(self._host, self._port, timeout=15) as server:
            server.starttls()
            if self._user:
                server.login(self._user, self._password or "")
            server.send_message(msg)
        return True
