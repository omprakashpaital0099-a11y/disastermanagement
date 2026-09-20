import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlertSubscription, HazardEvent, Severity
from app.services.notifier import notification_for, notifiers

logger = logging.getLogger("prithvinet.alerting")
severity_rank = {Severity.low: 1, Severity.watch: 2, Severity.high: 3, Severity.critical: 4}


async def evaluate_event_alerts(session: AsyncSession, event: HazardEvent) -> int:
    subscriptions = list(await session.scalars(select(AlertSubscription).where(AlertSubscription.enabled.is_(True))))
    sent = 0
    for subscription in subscriptions:
        if severity_rank[event.severity] < severity_rank[subscription.minimum_severity]:
            continue
        if subscription.hazard_types and event.hazard_type.value not in subscription.hazard_types:
            continue
        if subscription.states and event.state not in subscription.states:
            continue
        notifier = notifiers.get(subscription.channel, notifiers["log"])
        await notifier.send(notification_for(event, subscription.channel, subscription.destination))
        sent += 1
    if sent:
        logger.info("event_id=%s matched_subscriptions=%s", event.id, sent)
    return sent
