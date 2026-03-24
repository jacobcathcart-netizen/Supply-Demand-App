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


# supply
@st.cache_data(show_spinner=False, ttl=1800)
def get_supply() -> pd.DataFrame:
    return fetch_df(
        """
        select *
        from SA.SUPPLY_DEMAND.SUPPLY
        """
    )


# regions
@st.cache_data(show_spinner=False, ttl=1800)
def get_regions_df() -> pd.DataFrame:
    return fetch_df(
        """
        select distinct REGION, COUNT AS HEADCOUNT
        from SA.SUPPLY_DEMAND.SUPPLY
        order by REGION
        """
    )


# demand weight
@st.cache_data(show_spinner=False, ttl=1800)
def get_demand_weight() -> pd.DataFrame:
    return fetch_df(
        """
        select *
        from SA.SUPPLY_DEMAND.DEMAND_WEIGHTS
        """
    )


# Demand
@st.cache_data(show_spinner=False, ttl=1800)
def get_demand() -> pd.DataFrame:
    return fetch_df(
        """
        select
            CCRID,
            PROJECT_NAME,
            MONTH_NUMBER,
            sum(HOURS) as HOURS
        from SA.SUPPLY_DEMAND.SUPPLY_DEMAND_DT
        group by 1, 2, 3
        """
    )


# Backlog


@st.cache_data(show_spinner=False, ttl=1800)
def get_cm_backlog() -> pd.DataFrame:
    return fetch_df(
        """
        select NAME AS REGION, PROJECT_NAME,CCRID,COUNT
        from sa.supply_demand.corrective_backlog
        """
    )


@st.cache_data(show_spinner=False, ttl=1800)
def get_pm_backlog() -> pd.DataFrame:
    return fetch_df(
        """
        select NAME AS REGION, PROJECT_NAME,CCRID,COUNT
        from sa.supply_demand.preventive_backlog
        """
    )


@st.cache_data(show_spinner=False, ttl=1800)
def get_backlog(pm_assumption, cm_assumption) -> pd.DataFrame:
    return fetch_df(
        """
        select NAME AS REGION, PROJECT_NAME,CCRID,COUNT,COUNT * %s
        from sa.supply_demand.preventive_backlog
        UNION ALL 
        select NAME AS REGION, PROJECT_NAME,CCRID,COUNT, count * %s
        from sa.supply_demand.corrective_backlog
        
        """,
        (pm_assumption, cm_assumption),
    )


# Working days


@st.cache_data(show_spinner=False, ttl=1800)
def get_working_days(start_date, end_date) -> pd.DataFrame:
    return fetch_df(
        """
        with params as (
            select
                DATE_TRUNC('month',cast(%s as date)) as start_date,
                LAST_DAY(cast(%s as date)) as end_date
        ),
        holiday_list as (
            select
                CUSTRECORD_CCR_HOLIDAYS_DATE as holiday_date
            from STG.NETSUITE_SUITEANALYTICS_PRODUCTION.CUSTOMRECORD_CCR_HOLIDAYS
        ),
        calendar as (
            select dateadd(day, seq4(), p.start_date) as cal_date
            from params p, table(generator(rowcount => 15000))
            where dateadd(day, seq4(), p.start_date) <= p.end_date
        )
        select
            date_trunc('MONTH', cal_date) as MONTH_START,
            count(*) as BUSINESS_DAYS
        from calendar c
        left join holiday_list h
            on c.cal_date = h.holiday_date
        where dayofweekiso(c.cal_date) between 1 and 5
          and h.holiday_date is null
        group by 1
        order by 1
        """,
        (start_date.isoformat(), end_date.isoformat()),
    )
