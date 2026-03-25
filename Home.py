"""Landing page — connection diagnostics and quick-start guidance."""

import streamlit as st

from components.branding import apply_branding
from data.snowflake import get_connection_info, get_regions_df, reset_connection

st.set_page_config(page_title="Staffing Supply and Demand", layout="wide")
apply_branding()

st.title("Staffing Supply and Demand")
st.caption("Use the sidebar to navigate to **Inputs** to configure a scenario, then view **Results**.")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Test Connection"):
        try:
            st.dataframe(get_connection_info(), hide_index=True)
            st.success("Connected to Snowflake")
        except Exception as exc:
            st.error(f"Connection failed: {exc}")

with col2:
    if st.button("Load Regions"):
        try:
            regions_df = get_regions_df()
            if regions_df.empty:
                st.warning("No regions returned.")
            else:
                st.dataframe(regions_df, hide_index=True)
        except Exception as exc:
            st.error(f"Region query failed: {exc}")

with col3:
    if st.button("Reset Connection"):
        reset_connection()
        st.success("Snowflake connection reset.")
