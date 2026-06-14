"""Notifications: an in-app feed plus pluggable outbound channels
(console, Slack, Teams, email)."""

from app.notifications.base import Notification, NotificationChannel
from app.notifications.factory import get_notifier
from app.notifications.notifier import Notifier

__all__ = ["Notification", "NotificationChannel", "Notifier", "get_notifier"]
