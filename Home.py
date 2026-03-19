import streamlit as st

from data.snowflake import get_connection_info, get_regions_df, reset_connection


st.set_page_config(page_title="Staffing Supply and Demand", layout="wide")

st.title("Staffing Supply and Demand")
st.caption("Use the sidebar to configure a scenario and view results.")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Test Connection"):
        try:
            st.dataframe(get_connection_info(), use_container_width=True)
            st.success("Connected to Snowflake")
        except Exception as e:
            st.error(f"Connection failed: {e}")

with col2:
    if st.button("Load Regions"):
        try:
            st.dataframe(get_regions_df(), use_container_width=True)
        except Exception as e:
            st.error(f"Region query failed: {e}")

with col3:
    if st.button("Reset Connection"):
        reset_connection()
        st.success("Snowflake connection reset")