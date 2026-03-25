"""Snowflake data-access layer.

Every public ``get_*`` function returns a pandas DataFrame and is cached via
Streamlit's ``@st.cache_data`` decorator with a shared TTL from config.
"""

import pandas as pd
import snowflake.connector
import streamlit as st

from config import CACHE_TTL_SECONDS, SNOWFLAKE_SCHEMA

_SCHEMA = SNOWFLAKE_SCHEMA
_TTL = CACHE_TTL_SECONDS


# ── Connection management ────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_connection() -> snowflake.connector.SnowflakeConnection:
    """Return a cached Snowflake connection using Streamlit secrets."""
    return snowflake.connector.connect(
        user=st.secrets["snowflake"]["user"],
        account=st.secrets["snowflake"]["account"],
        authenticator=st.secrets["snowflake"].get("authenticator", "externalbrowser"),
        warehouse=st.secrets["snowflake"]["warehouse"],
        role=st.secrets["snowflake"]["role"],
        client_session_keep_alive=True,
    )


def reset_connection() -> None:
    """Close the current connection (if any) and clear the cache."""
    try:
        get_connection().close()
    except Exception:
        pass
    get_connection.clear()


def fetch_df(query: str, params: tuple | None = None) -> pd.DataFrame:
    """Execute *query* and return the result as a DataFrame."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(query, params) if params else cur.execute(query)
        df = cur.fetch_pandas_all()
    return df if df is not None else pd.DataFrame()


# ── Public query helpers ─────────────────────────────────────────────────────

def get_connection_info() -> pd.DataFrame:
    """Return a single-row frame with the current session context."""
    return fetch_df(
        """
        SELECT current_user(),
               current_role(),
               current_warehouse(),
               current_database(),
               current_schema()
        """
    )


@st.cache_data(show_spinner=False, ttl=_TTL)
def get_supply() -> pd.DataFrame:
    return fetch_df(f"SELECT * FROM {_SCHEMA}.SUPPLY")


@st.cache_data(show_spinner=False, ttl=_TTL)
def get_regions_df() -> pd.DataFrame:
    return fetch_df(
        f"""
        SELECT DISTINCT REGION, COUNT AS HEADCOUNT
        FROM {_SCHEMA}.SUPPLY
        ORDER BY REGION
        """
    )


@st.cache_data(show_spinner=False, ttl=_TTL)
def get_demand_weight() -> pd.DataFrame:
    return fetch_df(f"SELECT * FROM {_SCHEMA}.DEMAND_WEIGHTS")


@st.cache_data(show_spinner=False, ttl=_TTL)
def get_demand() -> pd.DataFrame:
    return fetch_df(
        f"""
        SELECT CCRID,
               PROJECT_NAME,
               MONTH_NUMBER,
               SUM(HOURS) AS HOURS
        FROM {_SCHEMA}.SUPPLY_DEMAND_DT
        GROUP BY 1, 2, 3
        """
    )


@st.cache_data(show_spinner=False, ttl=_TTL)
def get_cm_backlog() -> pd.DataFrame:
    return fetch_df(
        f"""
        SELECT NAME AS REGION, PROJECT_NAME, CCRID, COUNT
        FROM {_SCHEMA}.CORRECTIVE_BACKLOG
        """
    )


@st.cache_data(show_spinner=False, ttl=_TTL)
def get_pm_backlog() -> pd.DataFrame:
    return fetch_df(
        f"""
        SELECT NAME AS REGION, PROJECT_NAME, CCRID, COUNT
        FROM {_SCHEMA}.PREVENTIVE_BACKLOG
        """
    )


@st.cache_data(show_spinner=False, ttl=_TTL)
def get_backlog(pm_assumption: float, cm_assumption: float) -> pd.DataFrame:
    return fetch_df(
        f"""
        SELECT REGION, SUM(COUNT), SUM(HOURS)
        FROM (
            SELECT NAME AS REGION, COUNT, COUNT * %s AS HOURS
            FROM {_SCHEMA}.PREVENTIVE_BACKLOG
            UNION ALL
            SELECT NAME AS REGION, COUNT, COUNT * %s AS HOURS
            FROM {_SCHEMA}.CORRECTIVE_BACKLOG
        )
        GROUP BY 1
        """,
        (pm_assumption, cm_assumption),
    )


@st.cache_data(show_spinner=False, ttl=_TTL)
def get_working_days(start_date, end_date) -> pd.DataFrame:
    return fetch_df(
        """
        WITH params AS (
            SELECT DATE_TRUNC('month', CAST(%s AS DATE)) AS start_date,
                   LAST_DAY(CAST(%s AS DATE))             AS end_date
        ),
        holiday_list AS (
            SELECT CUSTRECORD_CCR_HOLIDAYS_DATE AS holiday_date
            FROM STG.NETSUITE_SUITEANALYTICS_PRODUCTION.CUSTOMRECORD_CCR_HOLIDAYS
        ),
        calendar AS (
            SELECT DATEADD(DAY, SEQ4(), p.start_date) AS cal_date
            FROM params p, TABLE(GENERATOR(ROWCOUNT => 15000))
            WHERE DATEADD(DAY, SEQ4(), p.start_date) <= p.end_date
        )
        SELECT DATE_TRUNC('MONTH', cal_date) AS MONTH_START,
               COUNT(*)                      AS BUSINESS_DAYS
        FROM calendar c
        LEFT JOIN holiday_list h ON c.cal_date = h.holiday_date
        WHERE DAYOFWEEKISO(c.cal_date) BETWEEN 1 AND 5
          AND h.holiday_date IS NULL
        GROUP BY 1
        ORDER BY 1
        """,
        (start_date.isoformat(), end_date.isoformat()),
    )
