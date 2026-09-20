from __future__ import annotations

import streamlit as st

from components.dashboard import load_data, setup_page, t

setup_page(t("authority"))

sensor, _, alerts, _ = load_data()
try:
    flame = bool(sensor and sensor.get("flame_sensor") is not None and float(sensor["flame_sensor"]) > 0)
except (TypeError, ValueError):
    flame = False

st.markdown('<div class="kicker">SPATIAL X / RESPONSE COORDINATION</div>', unsafe_allow_html=True)
st.markdown(f'<div class="title">{t("authority")}</div>', unsafe_allow_html=True)
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
        st.checkbox(action, key=f"response_action_{action}")
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
        message = f"**{severity}** · {item.get('title', 'Hazard event')} · {item.get('location_name', 'Location unavailable')}"
        st.warning(message) if severity in {"HIGH", "WATCH"} else st.error(message) if severity == "CRITICAL" else st.info(message)

st.subheader("Community response")
st.text_area("Response note", placeholder="Record authority or community coordination notes.")
st.button("Send authority update", type="primary")
