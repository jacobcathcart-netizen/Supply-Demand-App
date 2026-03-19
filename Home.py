import streamlit as st
import snowflake.connector


st.set_page_config(page_title="Staffing Supply and Demand", layout="wide")


@st.cache_resource
def get_snowflake_connection():
    return snowflake.connector.connect(
        user=st.secrets["snowflake"]["user"],
        account=st.secrets["snowflake"]["account"],
        authenticator=st.secrets["snowflake"].get("authenticator", "externalbrowser"),
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"],
    )


st.title("Staffing Supply and Demand")
st.caption("Use the sidebar to configure a scenario and view results.")

st.markdown(
    """
### Pages
- **Inputs**: Select timeframe, regions, and scenario assumptions
- **Results**: View project level supply, demand, and gap
"""
)

st.subheader("Snowflake Connection")

if st.button("Test Snowflake Connection"):
    try:
        conn = get_snowflake_connection()
        cur = conn.cursor()
        try:
            cur.execute("select current_user(), current_role(), current_warehouse()")
            user, role, warehouse = cur.fetchone()
            st.success("Connected to Snowflake")
            st.write(
                {
                    "user": user,
                    "role": role,
                    "warehouse": warehouse,
                }
            )
        finally:
            cur.close()
    except Exception as e:
        st.error(f"Connection failed: {e}")