from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas import SensorReading


class ThingSpeakError(RuntimeError):
    pass


FIELD_NAMES = (
    "soil_moisture",
    "water_level",
    "temperature",
    "humidity",
    "rainfall",
)


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reading(feed: dict[str, Any]) -> SensorReading:
    timestamp = feed.get("created_at")
    if not timestamp:
        raise ThingSpeakError("ThingSpeak response did not include a timestamp")
    return SensorReading(
        timestamp=datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
        **{name: _number(feed.get(f"field{index}")) for index, name in enumerate(FIELD_NAMES, start=1)},
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