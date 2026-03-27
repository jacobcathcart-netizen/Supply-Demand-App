"""Landing page — system status and quick navigation."""

import streamlit as st

from components.branding import (
    GRAY_600,
    HERO_IMAGE_PATH,
    LIGHT_BLUE,
    NAVY,
    TEAL,
    apply_branding,
    status_badge,
)
from config import build_demo_preset
from data.snowflake import get_connection_info, get_regions_df, reset_connection

st.set_page_config(
    page_title="Supply & Demand | CCR",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_branding()

# ── Hero banner ──────────────────────────────────────────────────────

hero_left, hero_right = st.columns([3, 2], gap="large")

with hero_left:
    st.markdown(
        f"""
        <div style="padding:1rem 0;">
            <h1 style="border-bottom:none;margin-bottom:0.5rem;font-size:2.2rem;">
                Staffing Supply &amp; Demand
            </h1>
            <p style="color:{GRAY_600};font-size:1.05rem;font-family:Tahoma,sans-serif;
                      margin:0;max-width:640px;">
                Model workforce capacity against project demand. Configure scenarios,
                adjust headcount, and analyse supply gaps across regions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with hero_right:
    if HERO_IMAGE_PATH.exists():
        st.image(
            str(HERO_IMAGE_PATH),
            caption="Rutherford Farm — Cypress Creek Renewables",
        )

# ── Quick actions ────────────────────────────────────────────────────

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Configure Inputs", width="stretch"):
        st.switch_page("pages/1_Inputs.py")
    st.caption("Set scenario parameters, regions, and headcount adjustments.")

with col2:
    if st.button("Load Demo & Run", type="primary", width="stretch"):
        st.session_state.update(inputs_saved=True, **build_demo_preset())
        st.switch_page("pages/2_Results.py")
    st.caption("Run a pre-configured demo scenario with randomised inputs.")

with col3:
    if st.button("View Results", width="stretch"):
        st.switch_page("pages/2_Results.py")
    st.caption("Analyse KPIs, charts, and backlog trends.")

# ── System diagnostics ───────────────────────────────────────────────

with st.expander("System Diagnostics", expanded=False):
    d1, d2, d3, d4 = st.columns(4)

    with d1:
        if st.button("Test Connection", width="stretch"):
            try:
                info = get_connection_info()
                st.dataframe(info, hide_index=True)
                st.markdown(status_badge("Connected", TEAL), unsafe_allow_html=True)
            except Exception as exc:
                st.error(f"Connection failed: {exc}")

    with d2:
        if st.button("Load Regions", width="stretch"):
            try:
                regions_df = get_regions_df()
                if regions_df.empty:
                    st.warning("No regions returned.")
                else:
                    st.dataframe(regions_df, hide_index=True)
                    st.markdown(
                        status_badge(f"{len(regions_df)} regions loaded", TEAL),
                        unsafe_allow_html=True,
                    )
            except Exception as exc:
                st.error(f"Region query failed: {exc}")

    with d3:
        if st.button("Reset Connection", width="stretch"):
            reset_connection()
            st.markdown(
                status_badge("Connection reset", LIGHT_BLUE),
                unsafe_allow_html=True,
            )

    with d4:
        if st.button("Clear Data Cache", width="stretch"):
            st.cache_data.clear()
            st.markdown(
                status_badge("Data cache cleared", LIGHT_BLUE),
                unsafe_allow_html=True,
            )
