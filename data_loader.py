"""Data access for the Streamlit dashboard."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st


class DataSourceError(RuntimeError):
    """Raised when a configured source cannot provide valid data."""


KNOWN_FIELD_NAMES = {
    "field1": "soil_moisture",
    "field2": "water_level",
    "field3": "temperature",
    "field4": "humidity",
    "field5": "flame_sensor",
    "field6": "rainfall",
}


def _secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
    except (FileNotFoundError, KeyError):
        value = default
    return str(value).strip() if value is not None else default


def _thingspeak_channel_id() -> str:
    return _secret("THINGSPEAK_CHANNEL_ID")


def get_thingspeak_channel_id() -> str:
    return _thingspeak_channel_id()


def _thingspeak_configured() -> bool:
    return bool(_thingspeak_channel_id())


def _number(value: Any) -> Any:
    if value in (None, ""):
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return value


def fetch_thingspeak_data(results: int = 20) -> pd.DataFrame:
    """Fetch and normalize recent readings directly from ThingSpeak."""
    channel_id = _thingspeak_channel_id()
    if not channel_id:
        raise DataSourceError("ThingSpeak channel ID is not configured in Streamlit secrets.")
    params: dict[str, str | int] = {"results": results}
    read_api_key = _secret("THINGSPEAK_READ_API_KEY")
    if read_api_key:
        params["api_key"] = read_api_key
    url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise DataSourceError("ThingSpeak could not be reached.") from error

    feeds = payload.get("feeds") if isinstance(payload, dict) else None
    if not isinstance(feeds, list) or not feeds:
        raise DataSourceError("ThingSpeak returned no sensor readings.")

    records: list[dict[str, Any]] = []
    for feed in feeds:
        if not isinstance(feed, dict):
            continue
        record: dict[str, Any] = {"timestamp": feed.get("created_at")}
        for key, value in feed.items():
            if key.startswith("field"):
                record[key] = _number(value)
                if key in KNOWN_FIELD_NAMES:
                    record[KNOWN_FIELD_NAMES[key]] = record[key]
        records.append(record)
    frame = pd.DataFrame(records)
    if frame.empty:
        raise DataSourceError("ThingSpeak returned no usable sensor readings.")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    if frame.empty:
        raise DataSourceError("ThingSpeak returned readings without valid timestamps.")
    return frame


def _thingspeak_latest(frame: pd.DataFrame) -> dict[str, Any]:
    latest = frame.iloc[-1].dropna().to_dict()
    latest["timestamp"] = frame.iloc[-1]["timestamp"].isoformat()
    return latest


def get_sensor_source_status() -> tuple[str, str | None]:
    return ("ThingSpeak", None) if _thingspeak_configured() else ("Backend/local fallback", None)


def _api_base() -> str:
    return os.getenv("PRITHVINET_API_URL", "http://localhost:8000/api/v1").rstrip("/")


def _request(path: str, params: dict[str, Any] | None = None) -> Any:
    try:
        response = requests.get(f"{_api_base()}/{path.lstrip('/')}", params=params, timeout=8)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        raise DataSourceError("The environmental API is temporarily unavailable.") from error


def _local_path() -> Path | None:
    configured = os.getenv("SENSOR_DATA_FILE", "").strip()
    return Path(configured) if configured else None


def _local_records() -> list[dict[str, Any]]:
    path = _local_path()
    if not path or not path.exists():
        return []
    try:
        if path.suffix.lower() == ".csv":
            return pd.read_csv(path).to_dict(orient="records")
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload = payload.get("readings", payload.get("data", []))
            return payload if isinstance(payload, list) else []
    except (OSError, ValueError, TypeError, pd.errors.ParserError) as error:
        raise DataSourceError("The configured local sensor file is invalid.") from error
    raise DataSourceError("Only JSON and CSV sensor files are supported.")


def get_sensor_data() -> dict[str, Any] | None:
    """Return the latest reading, or None when no source has data."""
    if _thingspeak_configured():
        try:
            return _thingspeak_latest(fetch_thingspeak_data(results=20))
        except DataSourceError:
            return None
    try:
        payload = _request("sensors/latest")
        return payload if isinstance(payload, dict) else None
    except DataSourceError:
        records = _local_records()
        return records[-1] if records else None


def get_sensor_history(results: int = 8000) -> pd.DataFrame:
    """Return timestamped readings from the API or configured JSON/CSV file."""
    if _thingspeak_configured():
        try:
            return fetch_thingspeak_data(results=min(results, 8000))
        except DataSourceError:
            return pd.DataFrame()
    try:
        payload = _request("sensors/history", {"results": results})
        records = payload if isinstance(payload, list) else []
    except DataSourceError:
        records = _local_records()
    frame = pd.DataFrame(records)
    if "timestamp" in frame:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
        frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp")
    return frame.reset_index(drop=True)


def get_alerts(limit: int = 100) -> list[dict[str, Any]]:
    try:
        payload = _request("hazards", {"limit": limit})
        return payload.get("items", []) if isinstance(payload, dict) else []
    except DataSourceError:
        return []


def get_sensor_locations() -> list[dict[str, Any]]:
    """Return locations only when a deployment provides coordinate data."""
    configured = os.getenv("SENSOR_LOCATIONS_FILE", "").strip()
    if not configured:
        return []
    path = Path(configured)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (OSError, ValueError):
        return []


def get_stats() -> dict[str, Any]:
    try:
        payload = _request("stats")
        return payload if isinstance(payload, dict) else {}
    except DataSourceError:
        return {}


def filter_history(frame: pd.DataFrame, period_days: int) -> pd.DataFrame:
    if frame.empty or "timestamp" not in frame:
        return frame
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
    return frame[frame["timestamp"] >= cutoff].copy()
