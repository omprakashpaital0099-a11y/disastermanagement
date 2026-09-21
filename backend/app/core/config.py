from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PrithviNet API"
    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./prithvinet.db"
    redis_url: str = ""
    hazard_cache_seconds: int = 30
    cwc_api_url: str = "https://example.invalid/cwc/river-gauges"
    cwc_api_key: str = ""
    cwc_interval_minutes: int = 15
    imd_api_url: str = "https://example.invalid/imd/weather"
    imd_api_key: str = ""
    imd_interval_minutes: int = 30
    imd_heavy_rainfall_mm: float = 115.6
    imd_watch_rainfall_mm: float = 64.5
    firms_api_url: str = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    firms_api_key: str = ""
    firms_interval_minutes: int = 15
    firms_days: int = 1
    cpcb_api_url: str = "https://example.invalid/cpcb/air-quality"
    cpcb_api_key: str = ""
    cpcb_interval_minutes: int = 20
    thingspeak_channel_id: str = ""
    thingspeak_read_api_key: str = ""
    thingspeak_write_api_key: str = ""
    thingspeak_api_url: str = "https://api.thingspeak.com"
    thingspeak_timeout_seconds: float = 10.0
    thingspeak_max_age_seconds: int = 300
    thingspeak_flame_field: int = 5
    thingspeak_rainfall_field: int = 6

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
