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

if HERO_IMAGE_PATH.exists():
    st.image(
        str(HERO_IMAGE_PATH),
        width="stretch",
    )

st.markdown(
    f"""
    <div style="padding:1.5rem 0 1rem;">
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

# ── Demo / Test button ───────────────────────────────────────────────

_, demo_col, _ = st.columns([1, 2, 1])
with demo_col:
    if st.button("🚀  Load Demo & Run", type="primary", width="stretch"):
        st.session_state.update(inputs_saved=True, **build_demo_preset())
        st.switch_page("pages/2_Results.py")

# ── Quick-start cards ─────────────────────────────────────────────────

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""
        <div style="background:white;border:1px solid #EEF1F6;border-radius:12px;
                    padding:1.5rem;height:180px;box-shadow:0 1px 3px rgba(10,51,112,0.06);">
            <div style="font-size:1.5rem;margin-bottom:0.75rem;">📝</div>
            <div style="font-weight:600;color:{NAVY};font-family:Tahoma,sans-serif;
                        font-size:1rem;margin-bottom:0.35rem;">
                1. Configure Inputs
            </div>
            <div style="color:{GRAY_600};font-size:0.85rem;font-family:Tahoma,sans-serif;">
                Set scenario parameters, select regions, and define headcount adjustments.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div style="background:white;border:1px solid #EEF1F6;border-radius:12px;
                    padding:1.5rem;height:180px;box-shadow:0 1px 3px rgba(10,51,112,0.06);">
            <div style="font-size:1.5rem;margin-bottom:0.75rem;">▶️</div>
            <div style="font-weight:600;color:{NAVY};font-family:Tahoma,sans-serif;
                        font-size:1rem;margin-bottom:0.35rem;">
                2. Run Scenario
            </div>
            <div style="color:{GRAY_600};font-size:0.85rem;font-family:Tahoma,sans-serif;">
                Execute the model to compute supply, demand, and gap projections.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div style="background:white;border:1px solid #EEF1F6;border-radius:12px;
                    padding:1.5rem;height:180px;box-shadow:0 1px 3px rgba(10,51,112,0.06);">
            <div style="font-size:1.5rem;margin-bottom:0.75rem;">📊</div>
            <div style="font-weight:600;color:{NAVY};font-family:Tahoma,sans-serif;
                        font-size:1rem;margin-bottom:0.35rem;">
                3. View Results
            </div>
            <div style="color:{GRAY_600};font-size:0.85rem;font-family:Tahoma,sans-serif;">
                Analyse KPIs, charts, and backlog trends. Download data as CSV.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── System status ─────────────────────────────────────────────────────

st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)

with st.expander("🔌  System Diagnostics", expanded=False):
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
