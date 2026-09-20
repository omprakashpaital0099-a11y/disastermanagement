from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import invalidate_hazard_cache
from app.models import EventStatus, HazardEvent
from app.services.alerting import evaluate_event_alerts
from app.services.risk_scoring import scorer


def first(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None and value != "":
            return value
    return default


def json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


async def upsert_events(session: AsyncSession, records: list[dict[str, Any]]) -> int:
    written = 0
    for record in records:
        latitude = float(record["latitude"])
        longitude = float(record["longitude"])
        values = {**record, "observed_at": record.get("observed_at") or datetime.now(timezone.utc), "location": f"POINT({longitude} {latitude})", "raw_payload": json_safe(record.get("raw_payload", record)), "status": record.get("status", EventStatus.active)}
        values["severity"] = scorer.score(values["hazard_type"], values["raw_payload"])
        event = await session.scalar(select(HazardEvent).where(HazardEvent.external_id == values["external_id"]))
        if event:
            for field, value in values.items():
                setattr(event, field, value)
        else:
            session.add(HazardEvent(**values))
        written += 1
    if written:
        await session.commit()
        for record in records:
            event = await session.scalar(select(HazardEvent).where(HazardEvent.external_id == record["external_id"]))
            if event:
                await evaluate_event_alerts(session, event)
        await invalidate_hazard_cache()
    return written
