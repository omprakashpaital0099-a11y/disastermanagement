from __future__ import annotations

import streamlit as st

from data_loader import get_alerts, get_sensor_data

st.set_page_config(page_title="SPATIAL X | Response", page_icon="🚨", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: Manrope, sans-serif; }
[data-testid="stAppViewContainer"] { background: #0f1416; }
.kicker { color:#b9df72; font:10px 'DM Mono',monospace; letter-spacing:.12em; text-transform:uppercase; }
.title { color:#e8e8e8; font-size:clamp(2rem,4vw,3.2rem); font-weight:800; letter-spacing:-.06em; margin:8px 0 18px; }
</style>
""", unsafe_allow_html=True)

st.page_link("app.py", label="← Back to overview")
st.markdown('<div class="kicker">SPATIAL X / RESPONSE COORDINATION</div>', unsafe_allow_html=True)
st.markdown('<div class="title">Response dashboard</div>', unsafe_allow_html=True)

sensor = get_sensor_data()
alerts = get_alerts()
try:
    flame = bool(sensor and sensor.get("flame_sensor") is not None and float(sensor["flame_sensor"]) > 0)
except (TypeError, ValueError):
    flame = False
if flame:
    st.error("CRITICAL · Flame detected. Immediate inspection required.")

columns = st.columns(4)
columns[0].metric("Active incidents", len(alerts) + int(flame))
columns[1].metric("Priority alerts", sum(str(item.get("severity", "")).lower() in {"high", "critical"} for item in alerts) + int(flame))
columns[2].metric("Response status", "DISPATCH REQUIRED" if flame else "MONITORING")
columns[3].metric("Emergency contact", "112")

left, right = st.columns(2)
with left:
    st.subheader("Recommended actions")
    actions = ["Review the latest sensor telemetry", "Confirm the incident location with field teams", "Record authority acknowledgement"]
    if flame:
        actions.insert(0, "Dispatch fire and emergency response immediately")
    for action in actions:
        st.checkbox(action, value=False, key=f"action_{action}")
with right:
    st.subheader("Authorities")
    st.dataframe([
        {"Authority": "Emergency services", "Contact": "112", "Status": "Ready"},
        {"Authority": "Fire response", "Contact": "101", "Status": "Ready"},
        {"Authority": "Police response", "Contact": "100", "Status": "Ready"},
    ], use_container_width=True, hide_index=True)

st.subheader("Priority incidents")
if not alerts and not flame:
    st.info("No active incidents are available from the backend.")
else:
    for item in alerts:
        severity = str(item.get("severity", "info")).upper()
        text = f"**{severity}** · {item.get('title', 'Hazard event')} · {item.get('location_name', 'Location unavailable')}"
        st.warning(text) if severity in {"HIGH", "WATCH"} else st.error(text) if severity == "CRITICAL" else st.info(text)

st.subheader("Community response")
st.text_area("Response note", placeholder="Record authority or community coordination notes.")
st.button("Send authority update", type="primary")
