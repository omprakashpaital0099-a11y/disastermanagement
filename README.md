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

The Streamlit dashboard connects directly to the configured ThingSpeak channel and exposes normalized readings in the live and history views:

```text
ThingSpeak -> data_loader.py -> Streamlit dashboard
```

Configure these values as Streamlit secrets (never commit `.streamlit/secrets.toml`):

```env
THINGSPEAK_CHANNEL_ID=3490996
THINGSPEAK_READ_API_KEY=009S8OH1DAIW04R7
```

The configured channel is public, so its read key may remain empty. A private channel requires its ThingSpeak read API key. The dashboard requests the latest 20 feeds directly, displays actual field values, and does not require `PRITHVINET_API_URL` for sensor data.
2. Open Streamlit Community Cloud and select **Deploy an app**.
3. Choose the repository and select `app.py` as the main file.
4. Add `THINGSPEAK_CHANNEL_ID` and, for private channels, `THINGSPEAK_READ_API_KEY` through Streamlit secrets. Do not commit `.streamlit/secrets.toml`.
5. Add other private values through Streamlit secrets or the deployment environment.
6. Deploy and verify the public URL, live sensor state, map, alert list, history controls, and response page.

The data flow is: ThingSpeak -> `data_loader.py` -> Streamlit cards and sensor history charts. Hazard events, maps, alerts, and response data continue to use the existing backend APIs.