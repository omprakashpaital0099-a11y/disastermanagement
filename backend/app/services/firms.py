import logging
import csv
from io import StringIO
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import HazardType, Severity
from app.services.hazard_writer import first, upsert_events
from app.services.ingestion_base import fetch_text, with_retries

logger = logging.getLogger("prithvinet.ingestion.firms")


@with_retries("nasa-firms", attempts=3)
async def ingest(session: AsyncSession) -> int:
    settings = get_settings()
    params = {"country": "IND", "days": settings.firms_days, "format": "json", "key": settings.firms_api_key}
    payload = await fetch_text(settings.firms_api_url, params=params)
    rows = list(csv.DictReader(StringIO(payload)))
    records = []
    for row in rows or []:
        confidence = str(first(row, "confidence", default="nominal")).lower()
        severity = Severity.high if confidence in {"high", "h"} else Severity.watch
        records.append({"external_id": f"firms-{first(row, 'frp', 'acq_date', default='event')}-{first(row, 'latitude', 'lat')}-{first(row, 'longitude', 'lon')}", "hazard_type": HazardType.fire, "severity": severity, "title": "NASA FIRMS thermal anomaly", "location_name": "India thermal hotspot", "state": first(row, "state", default="India"), "source": "NASA FIRMS", "description": f"Thermal anomaly detected; confidence {confidence}.", "latitude": first(row, "latitude", "lat"), "longitude": first(row, "longitude", "lon"), "observed_at": datetime.now(timezone.utc), "raw_payload": row})
    count = await upsert_events(session, [record for record in records if record["latitude"] is not None and record["longitude"] is not None])
    logger.info("source=NASA_FIRMS status=success records=%s", count)
    return count
