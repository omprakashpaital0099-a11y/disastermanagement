from __future__ import annotations

import streamlit as st

from components.dashboard import sidebar_controls, setup_page, t

st.set_page_config(page_title="SPATIAL X | Environmental Intelligence", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")
st.session_state.setdefault("language", "English")
st.session_state.setdefault("theme", "Dark")
setup_page(t("overview"))
sidebar_controls()

pages = {
    "Dashboard": [
        st.Page("pages/overview.py", title=t("overview"), icon="🏠", default=True),
        st.Page("pages/live_sensor_data.py", title=t("live"), icon="📡"),
        st.Page("pages/sensor_map.py", title=t("map"), icon="🗺️"),
        st.Page("pages/sensor_history.py", title=t("history"), icon="📈"),
        st.Page("pages/alerts.py", title=t("alerts"), icon="🚨"),
        st.Page("pages/risk_outlook.py", title=t("risk"), icon="⚠️"),
    ],
    "Intelligence": [
        st.Page("pages/environmental_intelligence.py", title=t("intelligence"), icon="🌱"),
        st.Page("pages/response.py", title=t("authority"), icon="🚑"),
    ],
}

pg = st.navigation(pages, position="sidebar", expanded=True)
pg.run()
