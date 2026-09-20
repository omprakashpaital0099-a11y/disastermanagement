# PrithviNet Backend

FastAPI backend for environmental hazard monitoring across India. It stores flood, fire, air-pollution, and water-pollution events in PostgreSQL/PostGIS, caches dashboard queries in Redis, and refreshes source data on independent APScheduler intervals.

## Ingestion sources

Each adapter lives in `app/services/` and owns its response normalization while sharing retry, logging, and PostGIS upsert helpers:

- `cwc.py`: Central Water Commission river gauge readings, flood severity from gauge versus danger level.
- `imd.py`: India Meteorological Department rainfall/weather readings, configurable rainfall thresholds.
- `firms.py`: NASA FIRMS thermal anomalies, CSV parsing and confidence-based fire severity.
- `cpcb.py`: Central Pollution Control Board air-quality readings, AQI-based severity.

Configure each provider URL, key, and interval in `.env`. Jobs execute immediately at startup and repeat independently. A failed source is retried three times with exponential backoff and logged with its source name; one source failure does not stop the others.

ThingSpeak sensor fields are mapped in order: `field1` soil moisture, `field2` water level, `field3` temperature, `field4` humidity, and `field5` rainfall. Set `THINGSPEAK_CHANNEL_ID` and `THINGSPEAK_READ_API_KEY` in `.env`; the read key is used only by FastAPI.

## Run locally

1. Copy `.env.example` to `.env` if you need to override the defaults.
2. For local development, the default configuration uses SQLite and an in-memory cache, so Docker is optional.
3. Start the API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the OpenAPI UI.

Docker Compose remains available for the PostgreSQL/PostGIS and Redis deployment used outside local development.

## API

- `GET /api/v1/health`
- `GET /api/v1/hazards?hazard_type=flood&severity=high&state=Assam`
- `GET /api/v1/hazards/{id}`
- `GET /api/v1/regions/{region_id}/risk-summary`
- `POST /api/v1/hazards`
- `POST /api/v1/alerts/subscribe`
- `GET /api/v1/stats`
- `GET /api/v1/sensors/latest`
- `GET /api/v1/sensors/history?results=100`

`GET /api/v1/hazards` also accepts `status`, `observed_from`, and `observed_to` filters. New events are scored by the rule-based scorer, persisted with their normalized status and raw provider payload, then evaluated against enabled subscriptions. The initial notifier is logging-only; a Twilio or SMS gateway can implement the `Notifier` interface in `app/services/notifier.py`.

The startup seed in `app/services/ingestion.py` keeps the API usable before provider credentials are configured. Replace the provider URLs with approved CWC, IMD, NASA FIRMS, and CPCB adapters as credentials become available.
