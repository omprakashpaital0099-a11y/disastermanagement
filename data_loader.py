"""Data access for the Streamlit dashboard."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


class DataSourceError(RuntimeError):
    """Raised when a configured source cannot provide valid data."""


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
    try:
        payload = _request("sensors/latest")
        return payload if isinstance(payload, dict) else None
    except DataSourceError:
        records = _local_records()
        return records[-1] if records else None


def get_sensor_history(results: int = 8000) -> pd.DataFrame:
    """Return timestamped readings from the API or configured JSON/CSV file."""
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
