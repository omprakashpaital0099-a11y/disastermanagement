import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models import HazardEvent

logger = logging.getLogger("prithvinet.alerting")


@dataclass(frozen=True)
class Notification:
    channel: str
    destination: str
    subject: str
    message: str


class Notifier(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> None:
        raise NotImplementedError


class LoggingNotifier(Notifier):
    async def send(self, notification: Notification) -> None:
        logger.info("notification channel=%s destination=%s subject=%s message=%s", notification.channel, notification.destination, notification.subject, notification.message)


notifiers: dict[str, Notifier] = {"log": LoggingNotifier()}


def notification_for(event: HazardEvent, channel: str, destination: str) -> Notification:
    return Notification(channel=channel, destination=destination, subject=f"{event.severity.value.upper()}: {event.title}", message=f"{event.location_name}, {event.state}: {event.description}")
