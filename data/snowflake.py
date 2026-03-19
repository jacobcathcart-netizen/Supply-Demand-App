import pandas as pd
import streamlit as st
import snowflake.connector


@st.cache_resource(show_spinner=False)
def get_connection():
    return snowflake.connector.connect(
        user=st.secrets["snowflake"]["user"],
        account=st.secrets["snowflake"]["account"],
        authenticator=st.secrets["snowflake"].get("authenticator", "externalbrowser"),
        warehouse=st.secrets["snowflake"]["warehouse"],
        role=st.secrets["snowflake"]["role"],
        client_session_keep_alive=True,
    )


def fetch_df(query: str, params: tuple | None = None) -> pd.DataFrame:
    conn = get_connection()
    with conn.cursor() as cur:
        if params is not None:
            cur.execute(query, params)
        else:
            cur.execute(query)
        df = cur.fetch_pandas_all()
    return df if df is not None else pd.DataFrame()


def reset_connection():
    try:
        conn = get_connection()
        conn.close()
    except Exception:
        pass
    get_connection.clear()


def get_connection_info() -> pd.DataFrame:
    return fetch_df(
        """
        select
            current_user(),
            current_role(),
            current_warehouse(),
            current_database(),
            current_schema()
        """
    )


@st.cache_data(show_spinner=False)
def get_regions_df() -> pd.DataFrame:
    return fetch_df(
        """
        select distinct REGION
        from SA.SUPPLY_DEMAND.SUPPLY
        order by REGION
        """
    )