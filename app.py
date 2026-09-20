from __future__ import annotations

import html
import os
from typing import Any

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from data_loader import DataSourceError, filter_history, get_alerts, get_sensor_data, get_sensor_history, get_sensor_locations, get_stats

st.set_page_config(page_title="SPATIAL X | Environmental Intelligence", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

TRANSLATIONS = {
    "English": {
        "overview": "Overview", "live": "Live Sensor Data", "map": "Sensor Map", "history": "Sensor History", "alerts": "Alerts", "response": "Response Team", "risk": "Risk Outlook", "intelligence": "Environmental Intelligence", "authority": "Authority / Community Response", "language": "Language", "theme": "Map theme", "light": "Light", "dark": "Dark", "title": "Environmental intelligence, without the guesswork.", "subtitle": "SPATIAL X unifies live telemetry, hazard events, and response coordination for faster decisions.", "unavailable": "Unavailable", "offline": "OFFLINE", "normal": "NORMAL", "warning": "WARNING", "critical": "CRITICAL", "no_flame": "NO FLAME DETECTED", "flame": "FLAME DETECTED", "response_open": "Open response dashboard", "source_unavailable": "Sensor data temporarily unavailable. Last successful update is not known.", "history_unavailable": "Historical data is unavailable from the configured source.", "period": "Time window", "hours": "24 hours", "days7": "7 days", "days30": "30 days", "last_update": "Last update", "sensor_data": "Live Sensor Data"
    },
    "हिंदी": {
        "overview": "अवलोकन", "live": "लाइव सेंसर डेटा", "map": "सेंसर मानचित्र", "history": "सेंसर इतिहास", "alerts": "चेतावनियाँ", "response": "प्रतिक्रिया टीम", "risk": "जोखिम अनुमान", "intelligence": "पर्यावरणीय जानकारी", "authority": "प्राधिकरण / सामुदायिक प्रतिक्रिया", "language": "भाषा", "theme": "मानचित्र थीम", "light": "लाइट", "dark": "डार्क", "title": "बिना अनुमान के पर्यावरणीय जानकारी।", "subtitle": "SPATIAL X लाइव टेलीमेट्री, खतरे की घटनाओं और प्रतिक्रिया समन्वय को एक साथ लाता है।", "unavailable": "उपलब्ध नहीं", "offline": "ऑफलाइन", "normal": "सामान्य", "warning": "चेतावनी", "critical": "गंभीर", "no_flame": "आग नहीं मिली", "flame": "आग का पता चला", "response_open": "प्रतिक्रिया डैशबोर्ड खोलें", "source_unavailable": "सेंसर डेटा अस्थायी रूप से उपलब्ध नहीं है। अंतिम सफल अपडेट ज्ञात नहीं है।", "history_unavailable": "कॉन्फ़िगर किए गए स्रोत से ऐतिहासिक डेटा उपलब्ध नहीं है।", "period": "समय सीमा", "hours": "24 घंटे", "days7": "7 दिन", "days30": "30 दिन", "last_update": "अंतिम अपडेट", "sensor_data": "लाइव सेंसर डेटा"
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


def inject_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: Manrope, sans-serif; }
    [data-testid="stAppViewContainer"] { background: #0f1416; }
    [data-testid="stSidebar"] { background: #102a24; }
    [data-testid="stSidebar"] * { color: #e9f2e8; }
    [data-testid="stMetric"] { background: #1a1f22; border: 1px solid #2c3635; border-radius: 8px; padding: 14px 16px; }
    [data-testid="stMetricLabel"] { color: #8b9991; } [data-testid="stMetricValue"] { color: #e8e8e8; }
    .kicker, .section-label { color: #b9df72; font: 10px 'DM Mono', monospace; letter-spacing: .12em; text-transform: uppercase; }
    .title { color:#e8e8e8; font-size:clamp(2rem,4vw,3.4rem); font-weight:800; letter-spacing:-.06em; line-height:1.02; margin:8px 0 12px; }
    .subtitle { color:#8b9991; font-size:14px; line-height:1.6; max-width:680px; }
    .section-label { color:#8b9991; margin:24px 0 12px; }
    .status-pill { display:inline-block; padding:4px 8px; border-radius:999px; font:9px 'DM Mono',monospace; letter-spacing:.08em; }
    .status-normal { background:rgba(185,223,114,.14); color:#b9df72; } .status-warning { background:rgba(232,163,59,.14); color:#e8a33b; } .status-critical { background:rgba(220,101,78,.14); color:#dc654e; } .status-offline { background:rgba(139,153,145,.14); color:#8b9991; }
    .flame-banner, .notice { border-radius:8px; padding:14px 16px; } .flame-banner { border:1px solid rgba(220,101,78,.55); background:rgba(220,101,78,.12); color:#f0a18f; font-weight:700; } .notice { border:1px solid #2c3635; background:#1a1f22; color:#8b9991; }
    </style>
    """, unsafe_allow_html=True)
    if st.session_state.get("theme") == t("light"):
        st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] { background: #f2f4ed; }
        [data-testid="stSidebar"] { background: #173f35; }
        [data-testid="stMetric"] { background: #fbfcf8; border-color: #dce3d9; }
        [data-testid="stMetricValue"] { color: #18231f; }
        .title { color: #18231f; } .subtitle { color: #60736a; }
        .notice { background: #fbfcf8; border-color: #dce3d9; color: #60736a; }
        </style>
        """, unsafe_allow_html=True)


def format_value(value: Any, unit: str) -> str:
    if value is None or pd.isna(value):
        return t("unavailable")
    return f"{float(value):.1f} {unit}" if unit != "value" else f"{float(value):.0f}"


def flame_detected(sensor: dict[str, Any] | None) -> bool | None:
    if not sensor or sensor.get("flame_sensor") is None:
        return None
    try:
        return float(sensor["flame_sensor"]) > 0
    except (TypeError, ValueError):
        return None


def sensor_status(sensor: dict[str, Any] | None, key: str) -> str:
    if not sensor or sensor.get(key) is None:
        return "offline"
    if key == "flame_sensor" and flame_detected(sensor):
        return "critical"
    return "normal"


def status_label(state: str) -> str:
    return {"normal": t("normal"), "warning": t("warning"), "critical": t("critical"), "offline": t("offline")}[state]


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### 🌿 SPATIAL X")
        st.caption("ENVIRONMENTAL INTELLIGENCE")
        language = st.selectbox(t("language"), ["English", "हिंदी"], index=0 if st.session_state.language == "English" else 1)
        st.session_state.language = language
        theme = st.selectbox(t("theme"), [t("dark"), t("light")], index=0 if st.session_state.theme == t("dark") else 1)
        st.session_state.theme = theme
        st.divider()
        st.markdown(f"**{t('overview')}**")
        for label in [t("live"), t("map"), t("history"), t("alerts"), t("risk"), t("intelligence"), t("authority")]:
            st.caption(label)
        st.divider()
        st.page_link("pages/response.py", label=t("response_open"), icon="🚨")
        st.caption(f"API: {os.getenv('PRITHVINET_API_URL', 'http://localhost:8000/api/v1')}")


def render_overview(sensor: dict[str, Any] | None, alerts: list[dict[str, Any]], stats: dict[str, Any]) -> None:
    st.markdown('<div class="section-label">NETWORK STATUS</div>', unsafe_allow_html=True)
    keys = list(SENSOR_META)
    online = sum(sensor is not None and sensor.get(key) is not None for key in keys)
    attention = sum(sensor_status(sensor, key) in {"warning", "critical"} for key in keys)
    timestamp = sensor.get("timestamp") if sensor else None
    update = timestamp[:19].replace("T", " ") if isinstance(timestamp, str) else t("unavailable")
    columns = st.columns(4)
    for column, label, value, delta in zip(columns, ["Total data channels", "Online channels", "Requiring attention", t("last_update")], [len(keys), online, attention, update], ["5 configured", "Live contract", "Sensor-derived", "UTC"]):
        column.metric(label, value, delta)
    flame = flame_detected(sensor)
    if flame is True:
        st.markdown(f'<div class="flame-banner">🔥 {t("critical")}: {t("flame")} · Immediate inspection required.</div>', unsafe_allow_html=True)
    elif flame is None:
        st.info("Flame sensor field is unavailable from the configured source; no emergency state is inferred.")
    st.markdown('<div class="section-label">RISK OUTLOOK</div>', unsafe_allow_html=True)
    high_events = sum(str(item.get("severity", "")).lower() in {"high", "critical"} for item in alerts)
    risk = "CRITICAL" if flame is True else "HIGH" if high_events else "LOW"
    reasons = (["Flame sensor is reporting a positive value."] if flame is True else []) + ([f"{high_events} high-severity hazard event(s) reported by the backend."] if high_events else ["No critical flame reading or high-severity hazard event is reported."])
    st.info(f"Risk Outlook: **{risk}**\n\n" + "\n".join(f"- {reason}" for reason in reasons))


def render_sensor_cards(sensor: dict[str, Any] | None) -> None:
    st.markdown(f'<div class="section-label">{t("sensor_data")}</div>', unsafe_allow_html=True)
    columns = st.columns(5)
    for column, key in zip(columns, SENSOR_META):
        english, hindi, unit, icon = SENSOR_META[key]
        label = hindi if st.session_state.language == "हिंदी" else english
        state = sensor_status(sensor, key)
        value = sensor.get(key) if sensor else None
        display = t("flame") if key == "flame_sensor" and value is not None and flame_detected(sensor) else t("no_flame") if key == "flame_sensor" and value is not None else format_value(value, unit)
        column.markdown(f"**{icon} {label}**<br><span class='status-pill status-{state}'>{status_label(state)}</span>", unsafe_allow_html=True)
        column.metric(label, display)
        if key == "flame_sensor" and value is not None:
            column.caption(f"Numeric value: {float(value):.0f}")
        column.caption(f"{t('last_update')}: {(sensor or {}).get('timestamp', t('unavailable'))}")


def render_map(alerts: list[dict[str, Any]], locations: list[dict[str, Any]]) -> None:
    st.markdown(f'<div class="section-label">{t("map")}</div>', unsafe_allow_html=True)
    dark = st.session_state.theme == t("dark")
    fmap = folium.Map(location=[22.5, 79.0], zoom_start=5, tiles="CartoDB dark_matter" if dark else "OpenStreetMap", control_scale=True)
    marker_count = 0
    for location in locations:
        try:
            lat, lon = float(location["latitude"]), float(location["longitude"])
            name = html.escape(str(location.get("name", "Sensor")))
            folium.Marker([lat, lon], tooltip=name, popup=folium.Popup(f"<b>{name}</b><br>Sensor location", max_width=240), icon=folium.Icon(color="green", icon="signal", prefix="fa")).add_to(fmap)
            marker_count += 1
        except (KeyError, TypeError, ValueError):
            continue
    colors = {"critical": "red", "high": "red", "watch": "orange", "low": "blue"}
    for hazard in alerts:
        try:
            lat, lon = float(hazard["latitude"]), float(hazard["longitude"])
            title = html.escape(str(hazard.get("title", "Hazard event")))
            severity = str(hazard.get("severity", "watch")).lower()
            popup = f"<b>{title}</b><br>{html.escape(str(hazard.get('location_name', '')))}<br>Severity: {html.escape(severity.upper())}"
            folium.Marker([lat, lon], tooltip=title, popup=folium.Popup(popup, max_width=260), icon=folium.Icon(color=colors.get(severity, "blue"), icon="exclamation-sign")).add_to(fmap)
            marker_count += 1
        except (KeyError, TypeError, ValueError):
            continue
    st_folium(fmap, use_container_width=True, height=480, returned_objects=[])
    if not marker_count:
        st.caption("No coordinate-bearing sensor or hazard records are available yet. The map is centered on India until locations arrive.")


def render_history(history: pd.DataFrame) -> None:
    st.markdown(f'<div class="section-label">{t("history")}</div>', unsafe_allow_html=True)
    selected = st.radio(t("period"), [t("hours"), t("days7"), t("days30")], horizontal=True)
    days = {t("hours"): 1, t("days7"): 7, t("days30"): 30}[selected]
    frame = filter_history(history, days)
    if frame.empty or "timestamp" not in frame:
        st.info(t("history_unavailable"))
        return
    available = [key for key in SENSOR_META if key in frame and frame[key].notna().any()]
    if not available:
        st.info(t("history_unavailable"))
        return
    chart = go.Figure()
    for key in available:
        english, hindi, unit, _ = SENSOR_META[key]
        label = hindi if st.session_state.language == "हिंदी" else english
        chart.add_trace(go.Scatter(x=frame["timestamp"], y=frame[key], mode="lines", name=f"{label} ({unit})"))
    chart.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#8b9991", legend=dict(orientation="h"))
    st.plotly_chart(chart, use_container_width=True)
    st.dataframe(frame.tail(20), use_container_width=True, hide_index=True)


def render_alerts(alerts: list[dict[str, Any]], sensor: dict[str, Any] | None) -> None:
    st.markdown(f'<div class="section-label">{t("alerts")}</div>', unsafe_allow_html=True)
    records = list(alerts)
    if flame_detected(sensor) is True:
        records.insert(0, {"severity": "critical", "title": "Flame detected", "location_name": "Sensor network", "description": "Immediate inspection required.", "observed_at": sensor.get("timestamp")})
    if not records:
        st.success("No active hazard alerts are reported by the backend.")
        return
    for alert in records[:12]:
        severity = str(alert.get("severity", "info")).upper()
        message = f"**{severity}** · {alert.get('title', 'Hazard event')}  \n{alert.get('location_name', 'Location unavailable')} · {alert.get('observed_at', t('unavailable'))}  \n{alert.get('description', 'No recommendation supplied by the source.')}"
        if severity == "CRITICAL": st.error(message)
        elif severity in {"HIGH", "WARNING", "WATCH"}: st.warning(message)
        else: st.info(message)


def main() -> None:
    st.session_state.setdefault("language", "English")
    st.session_state.setdefault("theme", t("dark"))
    inject_css()
    render_sidebar()
    st.markdown('<div class="kicker">SPATIAL X / ENVIRONMENTAL INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="title">{t("title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">{t("subtitle")}</div>', unsafe_allow_html=True)
    try:
        sensor, history, alerts, stats = get_sensor_data(), get_sensor_history(), get_alerts(), get_stats()
    except DataSourceError as error:
        sensor, history, alerts, stats = None, pd.DataFrame(), [], {}
        st.warning(str(error))
    if sensor is None:
        st.markdown(f'<div class="notice">{t("source_unavailable")}</div>', unsafe_allow_html=True)
    render_overview(sensor, alerts, stats)
    render_sensor_cards(sensor)
    render_map(alerts, get_sensor_locations())
    render_history(history)
    render_alerts(alerts, sensor)
    st.markdown(f'<div class="section-label">{t("authority")}</div>', unsafe_allow_html=True)
    st.page_link("pages/response.py", label=t("response_open"), icon="🚨")


if __name__ == "__main__":
    main()
