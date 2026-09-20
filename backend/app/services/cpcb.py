import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import HazardType, Severity
from app.services.hazard_writer import first, upsert_events
from app.services.ingestion_base import fetch_json, with_retries

logger = logging.getLogger("prithvinet.ingestion.cpcb")


@with_retries("cpcb", attempts=3)
async def ingest(session: AsyncSession) -> int:
    settings = get_settings()
    payload = await fetch_json(settings.cpcb_api_url, headers={"Authorization": f"Bearer {settings.cpcb_api_key}"} if settings.cpcb_api_key else None)
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    records = []
    for row in rows or []:
        aqi = float(first(row, "aqi", "AQI", default=0))
        pm25 = first(row, "pm25", "PM2.5", "pm2_5", default="n/a")
        severity = Severity.high if aqi >= 300 else Severity.watch if aqi >= 200 else Severity.low
        records.append({"external_id": f"cpcb-{first(row, 'station_id', 'stationId', 'id')}", "hazard_type": HazardType.air_pollution, "severity": severity, "title": "Air quality reading", "location_name": first(row, "station_name", "stationName", "city", default="CPCB station"), "state": first(row, "state", "state_name", default="India"), "source": "CPCB", "description": f"AQI {aqi}; PM2.5 {pm25}.", "latitude": first(row, "latitude", "lat"), "longitude": first(row, "longitude", "lon", "lng"), "observed_at": datetime.now(timezone.utc), "raw_payload": row})
    count = await upsert_events(session, [record for record in records if record["latitude"] is not None and record["longitude"] is not None])
    logger.info("source=CPCB status=success records=%s", count)
    return count
