from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas import SensorReading


class ThingSpeakError(RuntimeError):
    pass


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reading(feed: dict[str, Any]) -> SensorReading:
    settings = get_settings()
    timestamp = feed.get("created_at")
    if not timestamp:
        raise ThingSpeakError("ThingSpeak response did not include a timestamp")
    return SensorReading(
        timestamp=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
        soil_moisture=_number(feed.get("field1")),
        water_level=_number(feed.get("field2")),
        temperature=_number(feed.get("field5")),
        humidity=_number(feed.get("field6")),
        flame_sensor=_number(feed.get("field3")),
    )


async def _fetch_feeds(results: int) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.thingspeak_channel_id:
        raise ThingSpeakError("ThingSpeak channel is not configured")

    params: dict[str, str | int] = {"results": results}
    if settings.thingspeak_read_api_key:
        params["api_key"] = settings.thingspeak_read_api_key
    url = f"{settings.thingspeak_api_url.rstrip('/')}/channels/{settings.thingspeak_channel_id}/feeds.json"
    try:
        async with httpx.AsyncClient(timeout=settings.thingspeak_timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise ThingSpeakError("ThingSpeak is unavailable") from error

    feeds = payload.get("feeds") if isinstance(payload, dict) else None
    if not isinstance(feeds, list):
        raise ThingSpeakError("ThingSpeak returned an invalid feed response")
    return [feed for feed in feeds if isinstance(feed, dict)]


async def latest_reading() -> SensorReading:
    settings = get_settings()
    feeds = await _fetch_feeds(results=1)
    if not feeds:
        raise ThingSpeakError("ThingSpeak has no sensor readings")
    reading = _reading(feeds[-1])
    age_seconds = (datetime.now(timezone.utc) - reading.timestamp.astimezone(timezone.utc)).total_seconds()
    if age_seconds > settings.thingspeak_max_age_seconds:
        raise ThingSpeakError("ThingSpeak latest reading is stale")
    return reading


async def recent_readings(results: int = 100) -> list[SensorReading]:
    feeds = await _fetch_feeds(results=results)
    readings: list[SensorReading] = []
    for feed in feeds:
        try:
            readings.append(_reading(feed))
        except (ThingSpeakError, TypeError, ValueError):
            continue
    return readings


async def push_reading(reading: SensorReading) -> int:
    settings = get_settings()
    if not settings.thingspeak_channel_id:
        raise ThingSpeakError("ThingSpeak channel is not configured")
    if not settings.thingspeak_write_api_key:
        raise ThingSpeakError("ThingSpeak write API key is not configured")

    params: dict[str, str | float] = {"api_key": settings.thingspeak_write_api_key}
    values = {
        1: reading.soil_moisture,
        2: reading.water_level,
        3: reading.temperature,
        4: reading.humidity,
        settings.thingspeak_flame_field: reading.flame_sensor,
        settings.thingspeak_rainfall_field: reading.rainfall,
    }
    for field, value in values.items():
        if value is not None:
            params[f"field{field}"] = value

    url = f"{settings.thingspeak_api_url.rstrip('/')}/update"
    try:
        async with httpx.AsyncClient(timeout=settings.thingspeak_timeout_seconds) as client:
            response = await client.post(url, data=params)
            response.raise_for_status()
            entry_id = int(response.text.strip())
    except (httpx.HTTPError, ValueError) as error:
        raise ThingSpeakError("ThingSpeak rejected the sensor reading") from error
    if entry_id <= 0:
        raise ThingSpeakError("ThingSpeak rejected the sensor reading")
    return entry_id