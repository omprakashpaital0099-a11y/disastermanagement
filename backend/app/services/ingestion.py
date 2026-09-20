from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import invalidate_hazard_cache
from app.db import SessionLocal
from app.models import HazardEvent, HazardType, Severity
from app.services.hazard_writer import json_safe


MOCK_EVENTS = [
    {"external_id": "mock-gadchiroli-fire", "hazard_type": HazardType.fire, "severity": Severity.high, "title": "Forest fire activity", "location_name": "Gadchiroli", "state": "Maharashtra", "source": "thermal-satellite", "description": "Thermal confidence 92%; wind moving east at 18 km/h.", "latitude": 19.9, "longitude": 80.0},
    {"external_id": "mock-guwahati-flood", "hazard_type": HazardType.flood, "severity": Severity.watch, "title": "River level rising", "location_name": "Guwahati", "state": "Assam", "source": "river-gauge", "description": "Brahmaputra is 0.6m below warning stage.", "latitude": 26.1, "longitude": 91.7},
    {"external_id": "mock-delhi-air", "hazard_type": HazardType.air_pollution, "severity": Severity.high, "title": "Air quality shift", "location_name": "Delhi NCR", "state": "Delhi", "source": "air-quality-node", "description": "PM2.5 is 28% above the seven-day baseline.", "latitude": 28.6, "longitude": 77.2},
    {"external_id": "mock-kerala-water", "hazard_type": HazardType.water_pollution, "severity": Severity.watch, "title": "Water quality watch", "location_name": "Ernakulam", "state": "Kerala", "source": "water-quality-node", "description": "Dissolved oxygen trend requires monitoring.", "latitude": 10.5, "longitude": 76.3},
    {"external_id": "mock-ranthambore-fire", "hazard_type": HazardType.fire, "severity": Severity.watch, "title": "Thermal anomaly", "location_name": "Ranthambore", "state": "Rajasthan", "source": "thermal-satellite", "description": "New hotspot cluster near the southern buffer.", "latitude": 25.8, "longitude": 76.5},
]


async def pull_hazard_data(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    written = 0
    for payload in MOCK_EVENTS:
        event = await session.scalar(select(HazardEvent).where(HazardEvent.external_id == payload["external_id"]))
        values = {**payload, "observed_at": now, "location": f"POINT({payload['longitude']} {payload['latitude']})", "raw_payload": json_safe(payload)}
        if event:
            for field, value in values.items():
                setattr(event, field, value)
        else:
            session.add(HazardEvent(**values))
        written += 1
    await session.commit()
    await invalidate_hazard_cache()
    return written


async def scheduled_hazard_pull() -> None:
    async with SessionLocal() as session:
        await pull_hazard_data(session)
