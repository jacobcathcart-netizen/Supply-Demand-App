"""Snowflake data-access functions.

Every public function returns a pandas DataFrame and uses Streamlit
caching so repeated calls within the TTL window are free.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import snowflake.connector
import streamlit as st

from config import CACHE_TTL_SECONDS, SNOWFLAKE_SCHEMA

# ── Connection management ───────────────────────────────────────────

_SCHEMA = SNOWFLAKE_SCHEMA
_TTL = CACHE_TTL_SECONDS

@st.cache_resource(show_spinner=False)
def _get_connection() -> snowflake.connector.SnowflakeConnection:
    """Return a long-lived, cached Snowflake connection."""
    cfg = st.secrets["snowflake"]
    return snowflake.connector.connect(
        user=cfg["user"],
        account=cfg["account"],
        authenticator=cfg.get("authenticator", "externalbrowser"),
        warehouse=cfg["warehouse"],
        role=cfg["role"],
        client_session_keep_alive=True,
    )


def _fetch_df(query: str, params: tuple[Any, ...] | None = None) -> pd.DataFrame:
    """Execute *query* and return results as a DataFrame.

    Raises ``snowflake.connector.Error`` on failure so callers can
    decide how to surface errors (e.g. ``st.error``).
    """
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(query, params) if params else cur.execute(query)
        result = cur.fetch_pandas_all()
    return result if result is not None else pd.DataFrame()


def reset_connection() -> None:
    """Close the current connection and clear the resource cache."""
    try:
        _get_connection().close()
    except Exception:
        pass
    _get_connection.clear()


# ── Query helpers ───────────────────────────────────────────────────


def get_connection_info() -> pd.DataFrame:
    """Lightweight query to verify the active session."""
    return _fetch_df(
        """
        SELECT current_user()      AS "User",
               current_role()      AS "Role",
               current_warehouse() AS "Warehouse",
               current_database()  AS "Database",
               current_schema()    AS "Schema"
        """
    )


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def get_regions_df() -> pd.DataFrame:
    """Distinct regions with current headcount."""
    return _fetch_df(
        """
        SELECT DISTINCT REGION, COUNT AS HEADCOUNT
        FROM SA.SUPPLY_DEMAND.SUPPLY
        ORDER BY REGION
        """
    )


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def get_supply() -> pd.DataFrame:
    """Full supply table (region × month-number × headcount)."""
    return _fetch_df("SELECT * FROM SA.SUPPLY_DEMAND.SUPPLY")


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def get_demand_weight() -> pd.DataFrame:
    """Demand allocation weights per project / region / month."""
    return _fetch_df("SELECT * FROM SA.SUPPLY_DEMAND.DEMAND_WEIGHTS")


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def get_demand() -> pd.DataFrame:
    """Aggregated demand hours by project and month."""
    return _fetch_df(
        """
        SELECT CCRID,
               PROJECT_NAME,
               MONTH_NUMBER,
               SUM(HOURS) AS HOURS
        FROM SA.SUPPLY_DEMAND.SUPPLY_DEMAND_DT
        GROUP BY 1, 2, 3
        """
    )


# ── Backlog queries ─────────────────────────────────────────────────


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def get_cm_backlog() -> pd.DataFrame:
    """Corrective-maintenance backlog by region / project."""
    return _fetch_df(
        """
        SELECT NAME AS REGION, PROJECT_NAME, CCRID, COUNT
        FROM SA.SUPPLY_DEMAND.CORRECTIVE_BACKLOG
        """
    )


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def get_pm_backlog() -> pd.DataFrame:
    """Preventive-maintenance backlog by region / project."""
    return _fetch_df(
        """
        SELECT NAME AS REGION, PROJECT_NAME, CCRID, COUNT
        FROM SA.SUPPLY_DEMAND.PREVENTIVE_BACKLOG
        """
    )


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def get_backlog(pm_hours: int, cm_hours: int) -> pd.DataFrame:
    """Combined PM + CM backlog, converted to hours using the given assumptions."""
    return _fetch_df(
        """
        SELECT REGION, SUM(COUNT), SUM(HOURS)
        FROM (
            SELECT NAME AS REGION, COUNT, COUNT * %s AS HOURS
            FROM SA.SUPPLY_DEMAND.PREVENTIVE_BACKLOG
            UNION ALL
            SELECT NAME AS REGION, COUNT, COUNT * %s AS HOURS
            FROM SA.SUPPLY_DEMAND.CORRECTIVE_BACKLOG
        )
        GROUP BY 1
        """,
        (pm_hours, cm_hours),
    )


# ── Calendar ────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def get_working_days(start_date: date, end_date: date) -> pd.DataFrame:
    """Business days per month (excludes weekends and NetSuite holidays)."""
    return _fetch_df(
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
            SELECT DATEADD(DAY, seq4(), p.start_date) AS cal_date
            FROM params p, TABLE(GENERATOR(ROWCOUNT => 15000))
            WHERE DATEADD(DAY, seq4(), p.start_date) <= p.end_date
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
