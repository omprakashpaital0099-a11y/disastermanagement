import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import HazardType, Severity
from app.services.hazard_writer import first, upsert_events
from app.services.ingestion_base import fetch_json, with_retries

logger = logging.getLogger("prithvinet.ingestion.imd")


@with_retries("imd", attempts=3)
async def ingest(session: AsyncSession) -> int:
    settings = get_settings()
    payload = await fetch_json(settings.imd_api_url, headers={"Authorization": f"Bearer {settings.imd_api_key}"} if settings.imd_api_key else None)
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    records = []
    for row in rows or []:
        rainfall = float(first(row, "rainfall_mm", "rainfall", "rain", default=0))
        severity = Severity.high if rainfall >= settings.imd_heavy_rainfall_mm else Severity.watch if rainfall >= settings.imd_watch_rainfall_mm else Severity.low
        records.append({"external_id": f"imd-{first(row, 'station_id', 'stationId', 'id')}", "hazard_type": HazardType.flood, "severity": severity, "title": "Heavy rainfall signal", "location_name": first(row, "station_name", "stationName", "district", default="IMD station"), "state": first(row, "state", "state_name", default="India"), "source": "IMD", "description": f"Rainfall observed: {rainfall}mm.", "latitude": first(row, "latitude", "lat"), "longitude": first(row, "longitude", "lon", "lng"), "observed_at": datetime.now(timezone.utc), "raw_payload": row})
    count = await upsert_events(session, [record for record in records if record["latitude"] is not None and record["longitude"] is not None])
    logger.info("source=IMD status=success records=%s", count)
    return count
