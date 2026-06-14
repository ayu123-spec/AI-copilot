"""Outbound notification primitives: the message payload and the channel
interface. Channels (console, Slack, Teams, email) implement ``send``.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# Severity ordering, used to filter low-priority notifications.
LEVELS: dict[str, int] = {"info": 0, "success": 1, "warning": 2, "error": 3}


@dataclass
class Notification:
    title: str
    body: str = ""
    level: str = "info"
    event_type: str = "general"
    meta: dict = field(default_factory=dict)


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """Deliver the notification. Return True on success."""
        ...
