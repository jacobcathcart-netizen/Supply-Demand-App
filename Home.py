"""Landing page — system status and quick navigation."""

import streamlit as st

from components.branding import (
    LIGHT_BLUE,
    NAVY,
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

st.markdown(
    f"""
    <div style="
        border-radius: 12px; overflow: hidden; margin-bottom: 2rem;
        background: linear-gradient(135deg, {LIGHT_BLUE} 0%, {NAVY} 100%);
        padding: 3rem 2.5rem;
    ">
        <h1 style="border-bottom:none;color:white;font-family:Tahoma,Geneva,sans-serif;
                   font-weight:700;font-size:2.4rem;margin-bottom:0.5rem;">
            Staffing Supply &amp; Demand
        </h1>
        <p style="color:rgba(255,255,255,0.85);font-size:1rem;max-width:600px;margin:0;
                  font-family:Tahoma,Geneva,sans-serif;">
            Model workforce capacity against project demand. Configure scenarios,
            adjust headcount, and analyse supply gaps across regions.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Auto-connect to Snowflake on open ────────────────────────────────

try:
    with st.spinner("Connecting to Snowflake..."):
        regions_df = get_regions_df()
    if not regions_df.empty:
        st.markdown(
            status_badge(f"Connected — {len(regions_df)} regions loaded"),
            unsafe_allow_html=True,
        )
    else:
        st.warning("Connected, but no regions returned.")
except Exception as exc:
    st.error(f"Snowflake connection failed: {exc}")

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
                st.markdown(status_badge("Connected"), unsafe_allow_html=True)
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
                        status_badge(f"{len(regions_df)} regions loaded"),
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
