from snowflake.snowpark.context import get_active_session

def get_session():
    return get_active_session()

def get_supply():
    session = get_session()
    return session.sql("SELECT * FROM SA.SUPPLY_DEMAND.SUPPLY")

def get_regions_df():
    # Returns Snowpark DF for caching and flexible use in UI
    return get_supply().select("REGION").distinct().sort("REGION")

def get_demand_weight():
    session = get_session()
    return session.sql("SELECT * FROM SA.SUPPLY_DEMAND.DEMAND_WEIGHTS")

def get_working_days(start_date, end_date):
    session = get_session()

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    return session.sql(f"""
WITH params AS (
  SELECT
    CAST('{start_str}' AS DATE) AS start_date,
    CAST('{end_str}' AS DATE) AS end_date
),
holiday_list AS (
  SELECT
    CUSTRECORD_CCR_HOLIDAYS_DATE AS holiday_date
  FROM STG.NETSUITE_SUITEANALYTICS_PRODUCTION.CUSTOMRECORD_CCR_HOLIDAYS
),
calendar AS (
  SELECT DATEADD(day, seq4(), p.start_date) AS cal_date
  FROM params p, TABLE(GENERATOR(ROWCOUNT => 15000))
  WHERE DATEADD(day, seq4(), p.start_date) <= p.end_date
)
SELECT
  DATE_TRUNC('MONTH', cal_date) AS month_start,
  COUNT(*) AS business_days
FROM calendar c
LEFT JOIN holiday_list h
  ON c.cal_date = h.holiday_date
WHERE DAYOFWEEKISO(c.cal_date) BETWEEN 1 AND 5
  AND h.holiday_date IS NULL
GROUP BY 1
ORDER BY 1
""")

def get_demand():
    session = get_session()
    return session.sql("""
SELECT
  CCRID,
  PROJECT_NAME,
  MONTH_NUMBER,
  SUM(HOURS) AS HOURS
FROM SA.SUPPLY_DEMAND.SUPPLY_DEMAND_DT
GROUP BY 1,2,3
""")