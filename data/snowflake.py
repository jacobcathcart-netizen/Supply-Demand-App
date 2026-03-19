import pandas as pd
import streamlit as st
import snowflake.connector


def get_connection():
    return snowflake.connector.connect(
        user=st.secrets["snowflake"]["user"],
        account=st.secrets["snowflake"]["account"],
        authenticator=st.secrets["snowflake"].get("authenticator", "externalbrowser"),
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"],
    )


def fetch_df(query: str, params: tuple | None = None) -> pd.DataFrame:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            df = cur.fetch_pandas_all()
    return df if df is not None else pd.DataFrame()


def get_supply() -> pd.DataFrame:
    return fetch_df(
        """
        select *
        from SA.SUPPLY_DEMAND.SUPPLY
        """
    )


def get_regions_df() -> pd.DataFrame:
    return fetch_df(
        """
        select distinct REGION
        from SA.SUPPLY_DEMAND.SUPPLY
        order by REGION
        """
    )


def get_demand_weight() -> pd.DataFrame:
    return fetch_df(
        """
        select *
        from SA.SUPPLY_DEMAND.DEMAND_WEIGHTS
        """
    )


def get_working_days(start_date, end_date) -> pd.DataFrame:
    return fetch_df(
        """
        with params as (
            select
                cast(%s as date) as start_date,
                cast(%s as date) as end_date
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
            date_trunc('MONTH', cal_date) as month_start,
            count(*) as business_days
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