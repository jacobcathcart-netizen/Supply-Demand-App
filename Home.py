import streamlit as st

from data.snowflake import get_connection_info, get_regions_df


st.set_page_config(page_title="Staffing Supply and Demand", layout="wide")

st.title("Staffing Supply and Demand")
st.caption("Use the sidebar to configure a scenario and view results.")

st.markdown(
    """
### Pages
- **Inputs**: Select timeframe, regions, and scenario assumptions
- **Results**: View project level supply, demand, and gap
"""
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Snowflake Connection")

    if st.button("Test Snowflake Connection"):
        try:
            connection_info = get_connection_info()
            st.success("Connected to Snowflake")
            st.dataframe(connection_info, use_container_width=True)
        except Exception as e:
            st.error(f"Connection failed: {e}")

with col2:
    st.subheader("Preview Regions")

    if st.button("Load Regions"):
        try:
            regions_df = get_regions_df()
            st.success("Regions loaded")
            st.dataframe(regions_df, use_container_width=True)
        except Exception as e:
            st.error(f"Region query failed: {e}")