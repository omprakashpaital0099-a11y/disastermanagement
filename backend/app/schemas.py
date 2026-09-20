from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import EventStatus, HazardType, Severity


class HazardCreate(BaseModel):
    external_id: str = Field(min_length=2, max_length=120)
    hazard_type: HazardType
    severity: Severity
    title: str = Field(min_length=2, max_length=180)
    location_name: str = Field(min_length=2, max_length=180)
    state: str = Field(min_length=2, max_length=80)
    source: str = Field(min_length=2, max_length=80)
    description: str
    latitude: float = Field(ge=6, le=38)
    longitude: float = Field(ge=68, le=98)
    observed_at: datetime
    raw_payload: dict = Field(default_factory=dict)
    status: EventStatus = EventStatus.active


class HazardRead(HazardCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class HazardPage(BaseModel):
    items: list[HazardRead]
    total: int
    limit: int
    offset: int


class HazardStats(BaseModel):
    active_alerts: int
    high_risk: int
    flood_events: int
    fire_events: int
    pollution_events: int


class RegionRiskSummary(BaseModel):
    region: str
    total_events: int
    active_events: int
    highest_severity: Severity | None
    by_type: dict[str, int]


class SensorReading(BaseModel):
    timestamp: datetime
    soil_moisture: float | None = None
    water_level: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    rainfall: float | None = None


class AlertSubscriptionCreate(BaseModel):
    channel: str = Field(default="log", pattern="^(log|sms|webhook)$")
    destination: str = Field(min_length=2, max_length=180)
    hazard_types: list[HazardType] | None = None
    states: list[str] | None = None
    minimum_severity: Severity = Severity.watch


class AlertSubscriptionRead(AlertSubscriptionCreate):
    id: int
    enabled: bool
    model_config = ConfigDict(from_attributes=True)
