# SPATIAL X Environmental Intelligence

The project now includes a Streamlit dashboard that preserves the existing SPATIAL X visual language and reads live telemetry and hazard events from the FastAPI backend.

## Run locally

Install the dashboard dependencies:

```powershell
pip install -r requirements.txt
```

Start the existing backend separately when live data is configured:

```powershell
cd backend
uvicorn app.main:app --reload
```

Start the dashboard from the project root:

```powershell
streamlit run app.py
```

The dashboard reads `PRITHVINET_API_URL` when set and otherwise uses `http://localhost:8000/api/v1`. If the API is unavailable, set `SENSOR_DATA_FILE` to a JSON or CSV file containing timestamped readings. Optional sensor coordinates can be supplied with `SENSOR_LOCATIONS_FILE` as a JSON list containing `name`, `latitude`, and `longitude`.

The map uses OpenStreetMap tiles and requires no API key. It is centered on India at latitude `22.5`, longitude `79.0`, with initial zoom `5` in both dashboard themes.

ThingSpeak field mapping is `field1` soil moisture, `field2` water level, `field3` temperature, `field4` humidity, `field5` flame sensor, and `field6` rainfall. A positive flame value produces a critical alert; missing flame data is shown as unavailable rather than as no flame.

## Streamlit Community Cloud

1. Push the repository to GitHub with `app.py` and `requirements.txt` at the repository root.

## ThingSpeak connection

The FastAPI service connects to the configured ThingSpeak channel and exposes the normalized readings to Streamlit:

```text
ThingSpeak -> backend/app/services/thingspeak.py -> /api/v1/sensors/latest
									 -> /api/v1/sensors/history
									 -> Streamlit dashboard
```

Configure these values in `backend/.env` (never commit that file):

```env
THINGSPEAK_CHANNEL_ID=3490996
THINGSPEAK_READ_API_KEY=HFM9GZC2AWR1V2FT
THINGSPEAK_WRITE_API_KEY=HFM9GZC2AWR1V2FT
THINGSPEAK_API_URL=https://api.thingspeak.com
THINGSPEAK_FLAME_FIELD=5
THINGSPEAK_RAINFALL_FIELD=6
```

The configured channel is public, so its read key may remain empty. A private channel requires its ThingSpeak read API key. The backend rejects stale latest readings using `THINGSPEAK_MAX_AGE_SECONDS`; historical readings remain available when the device has not reported recently.
2. Open Streamlit Community Cloud and select **Deploy an app**.
3. Choose the repository and select `app.py` as the main file.
4. Add `PRITHVINET_API_URL` through the app settings or environment configuration if the API is hosted elsewhere.
5. Add private values through Streamlit secrets or the deployment environment. Do not commit `.env` or `.streamlit/secrets.toml`.
6. Deploy and verify the public URL, live sensor state, map, alert list, history controls, and response page.

The data flow is: ThingSpeak or another provider -> FastAPI ingestion and `/api/v1` endpoints -> `data_loader.py` -> Streamlit cards, map, charts, alerts, and response dashboard.