from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import client, invalidate_hazard_cache
from app.core.config import get_settings
from app.db import get_session
from app.models import AlertSubscription, EventStatus, HazardEvent, HazardType, Severity
from app.schemas import AlertSubscriptionCreate, AlertSubscriptionRead, HazardCreate, HazardPage, HazardRead, HazardStats, RegionRiskSummary, SensorReading
from app.services.alerting import evaluate_event_alerts
from app.services.risk_scoring import scorer
from app.services.hazard_writer import json_safe
from app.services.thingspeak import ThingSpeakError, latest_reading, recent_readings

router = APIRouter(prefix="/api/v1", tags=["hazards"])
settings = get_settings()


def cache_key(hazard_type: str | None, severity: str | None, state: str | None, observed_from: datetime | None, observed_to: datetime | None, limit: int, offset: int) -> str:
    return f"hazards:{hazard_type}:{severity}:{state}:{observed_from}:{observed_to}:{limit}:{offset}"


def to_read(event: HazardEvent) -> HazardRead:
    return HazardRead.model_validate(event)


@router.get("/hazards", response_model=HazardPage)
async def list_hazards(
    hazard_type: HazardType | None = None,
    severity: Severity | None = None,
    event_status: EventStatus | None = Query(default=None, alias="status"),
    state: str | None = Query(default=None, min_length=2, max_length=80),
    observed_from: datetime | None = None,
    observed_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> HazardPage:
    key = cache_key(hazard_type.value if hazard_type else None, severity.value if severity else None, state, observed_from, observed_to, limit, offset) + f":{event_status}"
    cached = await client.get(key)
    if cached:
        return HazardPage.model_validate_json(cached)

    filters = []
    if hazard_type:
        filters.append(HazardEvent.hazard_type == hazard_type)
    if severity:
        filters.append(HazardEvent.severity == severity)
    if event_status:
        filters.append(HazardEvent.status == event_status)
    if state:
        filters.append(func.lower(HazardEvent.state) == state.lower())
    if observed_from:
        filters.append(HazardEvent.observed_at >= observed_from)
    if observed_to:
        filters.append(HazardEvent.observed_at <= observed_to)

    total = await session.scalar(select(func.count(HazardEvent.id)).where(*filters)) or 0
    result = await session.scalars(
        select(HazardEvent).where(*filters).order_by(HazardEvent.observed_at.desc()).limit(limit).offset(offset)
    )
    page = HazardPage(items=[to_read(item) for item in result], total=total, limit=limit, offset=offset)
    await client.setex(key, settings.hazard_cache_seconds, page.model_dump_json())
    return page


@router.get("/hazards/{hazard_id}", response_model=HazardRead)
async def get_hazard(hazard_id: int, session: AsyncSession = Depends(get_session)) -> HazardRead:
    event = await session.get(HazardEvent, hazard_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hazard event not found")
    return to_read(event)


@router.post("/hazards", response_model=HazardRead, status_code=status.HTTP_201_CREATED)
async def create_hazard(payload: HazardCreate, session: AsyncSession = Depends(get_session)) -> HazardRead:
    existing = await session.scalar(select(HazardEvent).where(HazardEvent.external_id == payload.external_id))
    values = payload.model_dump()
    values["location"] = f"POINT({payload.longitude} {payload.latitude})"
    values["raw_payload"] = json_safe(values.get("raw_payload", values))
    values["severity"] = scorer.score(payload.hazard_type, values["raw_payload"])
    if existing:
        for field, value in values.items():
            setattr(existing, field, value)
        event = existing
    else:
        event = HazardEvent(**values)
        session.add(event)
    await session.commit()
    await session.refresh(event)
    await evaluate_event_alerts(session, event)
    await invalidate_hazard_cache()
    return to_read(event)


@router.get("/stats", response_model=HazardStats)
async def hazard_stats(session: AsyncSession = Depends(get_session)) -> HazardStats:
    total = await session.scalar(select(func.count(HazardEvent.id))) or 0
    high = await session.scalar(select(func.count(HazardEvent.id)).where(HazardEvent.severity.in_([Severity.high, Severity.critical]))) or 0
    floods = await session.scalar(select(func.count(HazardEvent.id)).where(HazardEvent.hazard_type == HazardType.flood)) or 0
    fires = await session.scalar(select(func.count(HazardEvent.id)).where(HazardEvent.hazard_type == HazardType.fire)) or 0
    pollution = await session.scalar(select(func.count(HazardEvent.id)).where(HazardEvent.hazard_type.in_([HazardType.air_pollution, HazardType.water_pollution]))) or 0
    return HazardStats(active_alerts=total, high_risk=high, flood_events=floods, fire_events=fires, pollution_events=pollution)


@router.get("/regions/{region_id}/risk-summary", response_model=RegionRiskSummary)
async def region_risk_summary(region_id: str, session: AsyncSession = Depends(get_session)) -> RegionRiskSummary:
    events = list(await session.scalars(select(HazardEvent).where(func.lower(HazardEvent.state) == region_id.lower())))
    counts: dict[str, int] = {}
    for event in events:
        counts[event.hazard_type.value] = counts.get(event.hazard_type.value, 0) + 1
    severity_rank = {Severity.low: 1, Severity.watch: 2, Severity.high: 3, Severity.critical: 4}
    highest = max((event.severity for event in events), key=lambda item: severity_rank[item], default=None)
    return RegionRiskSummary(region=region_id, total_events=len(events), active_events=sum(event.status == EventStatus.active for event in events), highest_severity=highest, by_type=counts)


@router.post("/alerts/subscribe", response_model=AlertSubscriptionRead, status_code=status.HTTP_201_CREATED)
async def subscribe_to_alerts(payload: AlertSubscriptionCreate, session: AsyncSession = Depends(get_session)) -> AlertSubscriptionRead:
    subscription = AlertSubscription(**payload.model_dump())
    subscription.hazard_types = [item.value for item in payload.hazard_types] if payload.hazard_types else None
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return AlertSubscriptionRead.model_validate(subscription)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "prithvinet-api", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/sensors/latest", response_model=SensorReading)
async def sensor_latest() -> SensorReading:
    try:
        return await latest_reading()
    except ThingSpeakError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.get("/sensors/history", response_model=list[SensorReading])
async def sensor_history(results: int = Query(default=100, ge=1, le=8000)) -> list[SensorReading]:
    try:
        return await recent_readings(results=results)
    except ThingSpeakError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
