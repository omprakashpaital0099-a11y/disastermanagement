from __future__ import annotations

import html
from typing import Any

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from data_loader import filter_history, get_alerts, get_sensor_data, get_sensor_history, get_sensor_locations, get_stats

TRANSLATIONS = {
    "English": {
        "overview": "Overview", "live": "Live Sensor Data", "map": "Sensor Map", "history": "Sensor History", "alerts": "Alerts", "risk": "Risk Outlook", "intelligence": "Environmental Intelligence", "authority": "Authority / Community Response", "language": "Language", "theme": "Theme", "light": "Light", "dark": "Dark", "title": "Environmental intelligence.", "subtitle": "SPATIAL X unifies live telemetry, hazard events, and response coordination for faster decisions.", "unavailable": "Unavailable", "offline": "OFFLINE", "normal": "NORMAL", "warning": "WARNING", "critical": "CRITICAL", "no_flame": "NO FLAME DETECTED", "flame": "FLAME DETECTED", "last_update": "Last update", "period": "Time window", "hours": "24 hours", "days7": "7 days", "days30": "30 days", "history_unavailable": "Historical data is unavailable from the configured source.", "source_unavailable": "Sensor data temporarily unavailable. Last successful update is not known."
    },
    "Hindi": {
        "overview": "अवलोकन", "live": "लाइव सेंसर डेटा", "map": "सेंसर मानचित्र", "history": "सेंसर इतिहास", "alerts": "अलर्ट", "risk": "जोखिम पूर्वानुमान", "intelligence": "पर्यावरणीय इंटेलिजेंस", "authority": "प्राधिकरण / सामुदायिक प्रतिक्रिया", "language": "भाषा", "theme": "थीम", "light": "लाइट", "dark": "डार्क", "title": "बिना अनुमान के पर्यावरणीय जानकारी।", "subtitle": "SPATIAL X लाइव टेलीमेट्री, खतरे की घटनाओं और प्रतिक्रिया समन्वय को एक साथ लाता है।", "unavailable": "उपलब्ध नहीं", "offline": "ऑफलाइन", "normal": "सामान्य", "warning": "चेतावनी", "critical": "गंभीर", "no_flame": "आग नहीं मिली", "flame": "आग का पता चला", "last_update": "अंतिम अपडेट", "period": "समय सीमा", "hours": "24 घंटे", "days7": "7 दिन", "days30": "30 दिन", "history_unavailable": "कॉन्फ़िगर किए गए स्रोत से ऐतिहासिक डेटा उपलब्ध नहीं है।", "source_unavailable": "सेंसर डेटा अस्थायी रूप से उपलब्ध नहीं है। अंतिम सफल अपडेट ज्ञात नहीं है।"
    },
}
SENSOR_META = {
    "soil_moisture": ("Soil Moisture", "मिट्टी की नमी", "%", "💧"),
    "water_level": ("Water Level", "जल स्तर", "m", "〰️"),
    "temperature": ("Temperature", "तापमान", "°C", "◌"),
    "humidity": ("Humidity", "आर्द्रता", "%", "◒"),
    "flame_sensor": ("Flame Sensor", "फ्लेम सेंसर", "value", "🔥"),
}


def t(key: str) -> str:
    return TRANSLATIONS[st.session_state.get("language", "English")][key]


def setup_page(title: str) -> None:
    st.set_page_config(page_title=f"SPATIAL X | {title}", page_icon="🌿", layout="wide")
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: Manrope, sans-serif; }
    [data-testid="stAppViewContainer"] { background: #0f1416; }
    [data-testid="stSidebar"] { background: #102a24; }
    [data-testid="stSidebar"] * { color: #e9f2e8; }
    [data-testid="stMetric"] { background: #1a1f22; border: 1px solid #2c3635; border-radius: 8px; padding: 14px 16px; }
    [data-testid="stMetricLabel"] { color: #8b9991; } [data-testid="stMetricValue"] { color: #e8e8e8; }
    .kicker, .section-label { color:#b9df72; font:10px 'DM Mono',monospace; letter-spacing:.12em; text-transform:uppercase; }
    .title { color:#e8e8e8; font-size:clamp(2rem,4vw,3.4rem); font-weight:800; letter-spacing:-.06em; line-height:1.02; margin:8px 0 12px; }
    .subtitle { color:#8b9991; font-size:14px; line-height:1.6; max-width:680px; }
    .section-label { color:#8b9991; margin:24px 0 12px; }
    .status-pill { display:inline-block; padding:4px 8px; border-radius:999px; font:9px 'DM Mono',monospace; letter-spacing:.08em; }
    .status-normal { background:rgba(185,223,114,.14); color:#b9df72; } .status-warning { background:rgba(232,163,59,.14); color:#e8a33b; } .status-critical { background:rgba(220,101,78,.14); color:#dc654e; } .status-offline { background:rgba(139,153,145,.14); color:#8b9991; }
    </style>
    """, unsafe_allow_html=True)
    if st.session_state.get("theme") == "Light":
        st.markdown("<style>[data-testid='stAppViewContainer']{background:#f2f4ed}[data-testid='stMetric']{background:#fbfcf8;border-color:#dce3d9}[data-testid='stMetricValue'],.title{color:#18231f}.subtitle{color:#60736a}</style>", unsafe_allow_html=True)


def sidebar_controls() -> None:
    with st.sidebar:
        st.markdown("### 🌿 SPATIAL X")
        st.caption("ENVIRONMENTAL INTELLIGENCE")
        language = st.selectbox("Language / भाषा", ["English", "Hindi"], index=0 if st.session_state.language == "English" else 1, key="language_selector")
        st.session_state.language = language
        st.session_state.theme = st.selectbox(t("theme"), ["Dark", "Light"], index=0 if st.session_state.theme == "Dark" else 1, key="theme_selector")
        st.divider()
        st.caption(f"API: {__import__('os').getenv('PRITHVINET_API_URL', 'http://localhost:8000/api/v1')}")


def load_data() -> tuple[dict[str, Any] | None, pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    return get_sensor_data(), get_sensor_history(), get_alerts(), get_stats()


def flame_detected(sensor: dict[str, Any] | None) -> bool | None:
    try:
        return None if not sensor or sensor.get("flame_sensor") is None else float(sensor["flame_sensor"]) > 0
    except (TypeError, ValueError):
        return None


def sensor_status(sensor: dict[str, Any] | None, key: str) -> str:
    if not sensor or sensor.get(key) is None:
        return "offline"
    return "critical" if key == "flame_sensor" and flame_detected(sensor) else "normal"


def value_text(value: Any, unit: str) -> str:
    if value is None or pd.isna(value):
        return t("unavailable")
    return f"{float(value):.1f} {unit}" if unit != "value" else f"{float(value):.0f}"


def render_header() -> None:
    st.markdown('<div class="kicker">SPATIAL X / ENVIRONMENTAL INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="title">{t("title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">{t("subtitle")}</div>', unsafe_allow_html=True)


def render_overview(sensor: dict[str, Any] | None, alerts: list[dict[str, Any]]) -> None:
    st.markdown('<div class="section-label">NETWORK STATUS</div>', unsafe_allow_html=True)
    online = sum(sensor is not None and sensor.get(key) is not None for key in SENSOR_META)
    attention = sum(sensor_status(sensor, key) in {"warning", "critical"} for key in SENSOR_META)
    update = str(sensor.get("timestamp", t("unavailable")))[:19].replace("T", " ") if sensor else t("unavailable")
    for column, label, value, delta in zip(st.columns(4), ["Total data channels", "Online channels", "Requiring attention", t("last_update")], [5, online, attention, update], ["5 configured", "Live contract", "Sensor-derived", "UTC"]):
        column.metric(label, value, delta)
    flame = flame_detected(sensor)
    if flame is True:
        st.error(f"{t('critical')}: {t('flame')} - Immediate inspection required.")
    elif flame is None:
        st.info(f"{t('unavailable')}: Flame sensor data is not available.")
    high_events = sum(str(item.get("severity", "")).lower() in {"high", "critical"} for item in alerts)
    risk = "CRITICAL" if flame else "HIGH" if high_events else "LOW"
    st.info(f"Risk Outlook: **{risk}**\n\n- {high_events} high-severity backend event(s)." if high_events else f"Risk Outlook: **{risk}**\n\n- No critical flame reading or high-severity event reported.")


def render_sensor_cards(sensor: dict[str, Any] | None) -> None:
    st.markdown(f'<div class="section-label">{t("live")}</div>', unsafe_allow_html=True)
    for column, key in zip(st.columns(5), SENSOR_META):
        english, hindi, unit, icon = SENSOR_META[key]
        label = hindi if st.session_state.language == "Hindi" else english
        value = sensor.get(key) if sensor else None
        state = sensor_status(sensor, key)
        display = t("flame") if key == "flame_sensor" and value is not None and flame_detected(sensor) else t("no_flame") if key == "flame_sensor" and value is not None else value_text(value, unit)
        column.markdown(f"**{icon} {label}**<br><span class='status-pill status-{state}'>{state.upper()}</span>", unsafe_allow_html=True)
        column.metric(label, display)
        column.caption(f"{t('last_update')}: {(sensor or {}).get('timestamp', t('unavailable'))}")


def render_map(sensor: dict[str, Any] | None, alerts: list[dict[str, Any]]) -> None:
    st.markdown(f'<div class="section-label">{t("map")}</div>', unsafe_allow_html=True)
    fmap = folium.Map(location=[22.5, 79.0], zoom_start=5, tiles="OpenStreetMap", control_scale=True)
    styles = {"flame": ("red", "fire", "flame_sensor"), "flame_sensor": ("red", "fire", "flame_sensor"), "temperature": ("orange", "info-sign", "temperature"), "humidity": ("lightblue", "tint", "humidity"), "water": ("blue", "tint", "water_level"), "water_level": ("blue", "tint", "water_level"), "soil": ("green", "leaf", "soil_moisture"), "soil_moisture": ("green", "leaf", "soil_moisture")}
    for location in get_sensor_locations():
        try:
            sensor_type = str(location.get("sensor_type", location.get("type", "sensor"))).lower()
            color, icon, key = styles.get(sensor_type, ("green", "signal", None))
            value = location.get("value", sensor.get(key) if sensor and key else None)
            unit = SENSOR_META.get(key, ("", "", "", ""))[2]
            status = "Unavailable" if value is None else "CRITICAL" if key == "flame_sensor" and float(value) > 0 else "NORMAL"
            name = html.escape(str(location.get("name", "Sensor")))
            updated = html.escape(str(location.get("last_updated", (sensor or {}).get("timestamp", "Unavailable"))))
            popup = f"<b>{name}</b><br>Value: {html.escape(value_text(value, unit))}<br>Unit: {html.escape(unit or 'Unavailable')}<br>Status: {status}<br>Last update: {updated}"
            folium.Marker([float(location["latitude"]), float(location["longitude"])], tooltip=name, popup=folium.Popup(popup, max_width=260), icon=folium.Icon(color=color, icon=icon, prefix="fa")).add_to(fmap)
        except (KeyError, TypeError, ValueError):
            continue
    colors = {"critical": "red", "high": "red", "watch": "orange", "low": "blue"}
    for hazard in alerts:
        try:
            severity = str(hazard.get("severity", "watch")).lower()
            popup = f"<b>{html.escape(str(hazard.get('title', 'Hazard event')))}</b><br>{html.escape(str(hazard.get('location_name', '')))}<br>Severity: {severity.upper()}"
            folium.Marker([float(hazard["latitude"]), float(hazard["longitude"])], popup=folium.Popup(popup, max_width=260), icon=folium.Icon(color=colors.get(severity, "blue"), icon="exclamation-sign")).add_to(fmap)
        except (KeyError, TypeError, ValueError):
            continue
    st_folium(fmap, use_container_width=True, height=600, returned_objects=[])


def render_history(history: pd.DataFrame) -> None:
    st.markdown(f'<div class="section-label">{t("history")}</div>', unsafe_allow_html=True)
    selected = st.radio(t("period"), [t("hours"), t("days7"), t("days30")], horizontal=True, key="history_period")
    frame = filter_history(history, {t("hours"): 1, t("days7"): 7, t("days30"): 30}[selected])
    if frame.empty or "timestamp" not in frame:
        st.info(t("history_unavailable")); return
    chart = go.Figure()
    for key in SENSOR_META:
        if key in frame and frame[key].notna().any():
            chart.add_trace(go.Scatter(x=frame.timestamp, y=frame[key], mode="lines", name=SENSOR_META[key][0]))
    if not chart.data:
        st.info(t("history_unavailable")); return
    chart.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#8b9991")
    st.plotly_chart(chart, use_container_width=True); st.dataframe(frame.tail(20), use_container_width=True, hide_index=True)


def render_alerts(alerts: list[dict[str, Any]], sensor: dict[str, Any] | None) -> None:
    st.markdown(f'<div class="section-label">{t("alerts")}</div>', unsafe_allow_html=True)
    records = list(alerts)
    if flame_detected(sensor): records.insert(0, {"severity": "critical", "title": "Flame detected", "location_name": "Sensor network", "description": "Immediate inspection required."})
    if not records: st.success("No active hazard alerts are reported by the backend."); return
    for item in records:
        severity = str(item.get("severity", "info")).upper(); message = f"**{severity}** · {item.get('title', 'Hazard event')}\n\n{item.get('location_name', 'Location unavailable')} · {item.get('description', '')}"
        st.error(message) if severity == "CRITICAL" else st.warning(message) if severity in {"HIGH", "WATCH", "WARNING"} else st.info(message)


def overview_page() -> None:
    sensor, _, alerts, _ = load_data(); render_header(); render_overview(sensor, alerts); render_sensor_cards(sensor)


def live_page() -> None:
    sensor, _, _, _ = load_data(); render_header(); render_sensor_cards(sensor)


def map_page() -> None:
    sensor, _, alerts, _ = load_data(); render_header(); render_map(sensor, alerts)


def history_page() -> None:
    _, history, _, _ = load_data(); render_header(); render_history(history)


def alerts_page() -> None:
    sensor, _, alerts, _ = load_data(); render_header(); render_alerts(alerts, sensor)


def risk_page() -> None:
    sensor, _, alerts, _ = load_data(); render_header(); render_overview(sensor, alerts)


def intelligence_page() -> None:
    sensor, history, alerts, _ = load_data(); render_header(); render_overview(sensor, alerts); render_sensor_cards(sensor); render_history(history)
