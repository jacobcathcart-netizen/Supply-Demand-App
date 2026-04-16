"""Snowflake data-access functions.

Every public function returns a pandas DataFrame and uses TTL-based
caching so repeated calls within the window are free.
"""

from __future__ import annotations

import os
import time
from datetime import date
from functools import wraps
from typing import Any

import pandas as pd
import snowflake.connector

from config import CACHE_TTL_SECONDS

# ── TTL cache decorator (replaces @st.cache_data) ────────────────────

def _ttl_cache(ttl: int = CACHE_TTL_SECONDS):
    """Simple TTL cache for functions returning DataFrames."""
    def decorator(fn):
        _cache: dict[str, tuple[float, Any]] = {}

        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__name__}:{args}:{kwargs}"
            now = time.time()
            if key in _cache:
                ts, val = _cache[key]
                if now - ts < ttl:
                    return val
            result = fn(*args, **kwargs)
            _cache[key] = (now, result)
            return result

        wrapper.clear = lambda: _cache.clear()
        return wrapper
    return decorator


# ── Connection management ───────────────────────────────────────────

_connection: snowflake.connector.SnowflakeConnection | None = None


def _get_connection() -> snowflake.connector.SnowflakeConnection:
    """Return a long-lived Snowflake connection (singleton)."""
    global _connection
    if _connection is not None:
        try:
            _connection.cursor().execute("SELECT 1")
            return _connection
        except Exception:
            _connection = None

    _connection = snowflake.connector.connect(
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ.get("SNOWFLAKE_PASSWORD", os.environ.get("SNOWFLAKE_TOKEN", "")),
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ["SNOWFLAKE_ROLE"],
        client_session_keep_alive=True,
    )
    return _connection


def _fetch_df(query: str, params: tuple[Any, ...] | None = None) -> pd.DataFrame:
    """Execute *query* and return results as a DataFrame."""
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(query, params) if params else cur.execute(query)
        result = cur.fetch_pandas_all()
    return result if result is not None else pd.DataFrame()


def reset_connection() -> None:
    """Close the current connection and clear caches."""
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None


def clear_data_cache() -> None:
    """Clear all TTL caches."""
    for fn in [
        get_regions_df, get_supply, get_demand_weight, get_demand,
        get_projects, get_cm_backlog, get_pm_backlog, get_backlog,
        get_working_days,
    ]:
        if hasattr(fn, "clear"):
            fn.clear()


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


@_ttl_cache()
def get_regions_df() -> pd.DataFrame:
    """Distinct regions with current headcount."""
    return _fetch_df(
        """
        SELECT DISTINCT REGION, COUNT AS HEADCOUNT
        FROM SA.SUPPLY_DEMAND.SUPPLY
        ORDER BY REGION
        """
    )


@_ttl_cache()
def get_supply() -> pd.DataFrame:
    """Full supply table (region x month-number x headcount)."""
    return _fetch_df("SELECT * FROM SA.SUPPLY_DEMAND.SUPPLY")


@_ttl_cache()
def get_demand_weight() -> pd.DataFrame:
    """Demand allocation weights per project / region / month."""
    return _fetch_df("SELECT * FROM SA.SUPPLY_DEMAND.DEMAND_WEIGHTS")


@_ttl_cache()
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


# ── Project dimension ──────────────────────────────────────────────


@_ttl_cache()
def get_projects() -> pd.DataFrame:
    """Project dimension table with metadata."""
    return _fetch_df(
        """
        SELECT ROLLUP_CUSTOMER AS CUSTOMER,
               PROJECT_NAME,
               PROJECT_NAME_CLEAN,
               CCRID,
               STATE,
               REGION,
               ACCOUNT_MANAGER,
               SITE_OPERATING_STATUS_C,
               O_M_SERVICES_COMMENCEMENT_DATE_C,
               TERMINATION_DATE_C,
               PV_KW_DC / 1000 AS PV_MWDC_C,
               "Int/Ext"
        FROM SA.STG.PROJECTS_DT
        """
    )


# ── Backlog queries ─────────────────────────────────────────────────


@_ttl_cache()
def get_cm_backlog() -> pd.DataFrame:
    """Corrective-maintenance backlog by region / project."""
    return _fetch_df(
        """
        SELECT NAME AS REGION, PROJECT_NAME, CCRID, COUNT
        FROM SA.SUPPLY_DEMAND.CORRECTIVE_BACKLOG
        """
    )


@_ttl_cache()
def get_pm_backlog() -> pd.DataFrame:
    """Preventive-maintenance backlog by region / project."""
    return _fetch_df(
        """
        SELECT NAME AS REGION, PROJECT_NAME, CCRID, COUNT
        FROM SA.SUPPLY_DEMAND.PREVENTIVE_BACKLOG
        """
    )


@_ttl_cache()
def get_backlog(pm_hours: int, cm_hours: int) -> pd.DataFrame:
    """Combined PM + CM backlog by region and project, converted to hours."""
    return _fetch_df(
        """
        SELECT  REGION, PROJECT_NAME, CCRID, SUM(COUNT) AS COUNT, SUM(HOURS) AS HOURS
        FROM (
            SELECT NAME AS  REGION, PROJECT_NAME, CCRID, COUNT, COUNT * %s AS HOURS
            FROM SA.SUPPLY_DEMAND.PREVENTIVE_BACKLOG
            UNION ALL
            SELECT NAME AS REGION,  PROJECT_NAME, CCRID, COUNT, COUNT * %s AS HOURS
            FROM SA.SUPPLY_DEMAND.CORRECTIVE_BACKLOG
        )
        GROUP BY 1, 2, 3
        """,
        (pm_hours, cm_hours),
    )


# ── Calendar ────────────────────────────────────────────────────────


@_ttl_cache()
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
