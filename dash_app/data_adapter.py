"""Snowflake data access with TTL caching (replaces Streamlit caching).

Mirrors the public API of ``data.snowflake`` so the rest of the Dash app
can import identically-named functions.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import date
from typing import Any

import pandas as pd
import snowflake.connector

from config import CACHE_TTL_SECONDS

# ── Simple TTL cache (avoids circular import with app.py) ──────────

_cache_store: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.Lock()


def _cache_get(key: str) -> Any | None:
    with _cache_lock:
        entry = _cache_store.get(key)
        if entry is None:
            return None
        ts, val = entry
        if time.time() - ts > CACHE_TTL_SECONDS:
            del _cache_store[key]
            return None
        return val


def _cache_set(key: str, val: Any) -> None:
    with _cache_lock:
        _cache_store[key] = (time.time(), val)


def _cache_clear() -> None:
    with _cache_lock:
        _cache_store.clear()


# ── Connection singleton ───────────────────────────────────────────

_conn: snowflake.connector.SnowflakeConnection | None = None
_lock = threading.Lock()


def _get_connection() -> snowflake.connector.SnowflakeConnection:
    """Return a long-lived Snowflake connection (thread-safe singleton)."""
    global _conn
    with _lock:
        if _conn is None or _conn.is_closed():
            _conn = snowflake.connector.connect(
                user=os.environ["SNOWFLAKE_USER"],
                password=os.environ.get(
                    "SNOWFLAKE_TOKEN", os.environ.get("SNOWFLAKE_PASSWORD", "")
                ),
                account=os.environ["SNOWFLAKE_ACCOUNT"],
                warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
                role=os.environ["SNOWFLAKE_ROLE"],
                client_session_keep_alive=True,
            )
        return _conn


def _fetch_df(query: str, params: tuple[Any, ...] | None = None) -> pd.DataFrame:
    conn = _get_connection()
    with conn.cursor() as cur:
        cur.execute(query, params) if params else cur.execute(query)
        result = cur.fetch_pandas_all()
    return result if result is not None else pd.DataFrame()


def reset_connection() -> None:
    """Close the current connection and clear caches."""
    global _conn
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None
    _cache_clear()


def get_connection_info() -> pd.DataFrame:
    return _fetch_df(
        """
        SELECT current_user()      AS "User",
               current_role()      AS "Role",
               current_warehouse() AS "Warehouse",
               current_database()  AS "Database",
               current_schema()    AS "Schema"
        """
    )


def get_regions_df() -> pd.DataFrame:
    rv = _cache_get("get_regions_df")
    if rv is not None:
        return rv
    rv = _fetch_df(
        """
        SELECT DISTINCT REGION, COUNT AS HEADCOUNT
        FROM SA.SUPPLY_DEMAND.SUPPLY
        ORDER BY REGION
        """
    )
    _cache_set("get_regions_df", rv)
    return rv


def get_supply() -> pd.DataFrame:
    rv = _cache_get("get_supply")
    if rv is not None:
        return rv
    rv = _fetch_df("SELECT * FROM SA.SUPPLY_DEMAND.SUPPLY")
    _cache_set("get_supply", rv)
    return rv


def get_demand_weight() -> pd.DataFrame:
    rv = _cache_get("get_demand_weight")
    if rv is not None:
        return rv
    rv = _fetch_df("SELECT * FROM SA.SUPPLY_DEMAND.DEMAND_WEIGHTS")
    _cache_set("get_demand_weight", rv)
    return rv


def get_demand() -> pd.DataFrame:
    rv = _cache_get("get_demand")
    if rv is not None:
        return rv
    rv = _fetch_df(
        """
        SELECT CCRID,
               PROJECT_NAME,
               MONTH_NUMBER,
               SUM(HOURS) AS HOURS
        FROM SA.SUPPLY_DEMAND.SUPPLY_DEMAND_DT
        GROUP BY 1, 2, 3
        """
    )
    _cache_set("get_demand", rv)
    return rv


def get_projects() -> pd.DataFrame:
    rv = _cache_get("get_projects")
    if rv is not None:
        return rv
    rv = _fetch_df(
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
    _cache_set("get_projects", rv)
    return rv


def get_cm_backlog() -> pd.DataFrame:
    rv = _cache_get("get_cm_backlog")
    if rv is not None:
        return rv
    rv = _fetch_df(
        """
        SELECT NAME AS REGION, PROJECT_NAME, CCRID, COUNT
        FROM SA.SUPPLY_DEMAND.CORRECTIVE_BACKLOG
        """
    )
    _cache_set("get_cm_backlog", rv)
    return rv


def get_pm_backlog() -> pd.DataFrame:
    rv = _cache_get("get_pm_backlog")
    if rv is not None:
        return rv
    rv = _fetch_df(
        """
        SELECT NAME AS REGION, PROJECT_NAME, CCRID, COUNT
        FROM SA.SUPPLY_DEMAND.PREVENTIVE_BACKLOG
        """
    )
    _cache_set("get_pm_backlog", rv)
    return rv


def get_backlog(pm_hours: int, cm_hours: int) -> pd.DataFrame:
    key = f"get_backlog_{pm_hours}_{cm_hours}"
    rv = _cache_get(key)
    if rv is not None:
        return rv
    rv = _fetch_df(
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
    _cache_set(key, rv)
    return rv


def get_working_days(start_date: date, end_date: date) -> pd.DataFrame:
    key = f"get_working_days_{start_date}_{end_date}"
    rv = _cache_get(key)
    if rv is not None:
        return rv
    rv = _fetch_df(
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
    _cache_set(key, rv)
    return rv
