import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import HazardType, Severity
from app.services.hazard_writer import first, upsert_events
from app.services.ingestion_base import fetch_json, with_retries

logger = logging.getLogger("prithvinet.ingestion.cwc")


@with_retries("cwc", attempts=3)
async def ingest(session: AsyncSession) -> int:
    settings = get_settings()
    payload = await fetch_json(settings.cwc_api_url, headers={"Authorization": f"Bearer {settings.cwc_api_key}"} if settings.cwc_api_key else None)
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    records = []
    for row in rows or []:
        level = float(first(row, "water_level", "level", "gauge_level", default=0))
        danger = float(first(row, "danger_level", "dangerLevel", default=level + 1))
        records.append({"external_id": f"cwc-{first(row, 'station_id', 'stationId', 'id')}", "hazard_type": HazardType.flood, "severity": Severity.high if level >= danger else Severity.watch, "title": "River gauge level update", "location_name": first(row, "station_name", "stationName", default="CWC gauge"), "state": first(row, "state", "state_name", default="India"), "source": "CWC", "description": f"Water level {level}m; danger level {danger}m.", "latitude": first(row, "latitude", "lat"), "longitude": first(row, "longitude", "lon", "lng"), "observed_at": datetime.now(timezone.utc), "raw_payload": row})
    count = await upsert_events(session, [record for record in records if record["latitude"] is not None and record["longitude"] is not None])
    logger.info("source=CWC status=success records=%s", count)
    return count
