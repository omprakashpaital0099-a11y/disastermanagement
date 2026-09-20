import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class HazardType(str, enum.Enum):
    flood = "flood"
    fire = "fire"
    air_pollution = "air_pollution"
    water_pollution = "water_pollution"


class Severity(str, enum.Enum):
    low = "low"
    watch = "watch"
    high = "high"
    critical = "critical"


class EventStatus(str, enum.Enum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"


class AlertSubscription(Base):
    __tablename__ = "alert_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(30), default="log")
    destination: Mapped[str] = mapped_column(String(180))
    hazard_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    states: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    minimum_severity: Mapped[Severity] = mapped_column(Enum(Severity, name="subscription_minimum_severity"), default=Severity.watch)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HazardEvent(Base):
    __tablename__ = "hazard_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    hazard_type: Mapped[HazardType] = mapped_column(Enum(HazardType, name="hazard_type"), index=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    location_name: Mapped[str] = mapped_column(String(180), index=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location: Mapped[str] = mapped_column(String(80))
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus, name="event_status"), default=EventStatus.active, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
