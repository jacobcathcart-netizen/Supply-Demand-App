from snowflake.snowpark import Row
from snowflake.snowpark.functions import (
    col,
    lit,
    when,
    month,
    greatest,
    round as sround,
)
from snowflake.snowpark.context import get_active_session
from data.snowflake import (
    get_supply,
    get_working_days,
    get_demand_weight,
    get_demand,
)

session = get_active_session()


def run_scenario(
    regions,
    adjustments,
    start_date,
    end_date,
    adjustment_start_date,
    pct_decrease,
    vac_days_per_month,
    sick_days_per_month,
):
    # Base supply by region and month number, expanded across selected date range via month_number join
    supply = get_supply().filter(col("REGION").isin(regions))

    wd = (
        get_working_days(start_date, end_date)
        .with_column("MONTH_NUMBER", month(col("MONTH_START")))
        .select("MONTH_START", "MONTH_NUMBER", "BUSINESS_DAYS")
    )

    adj_df = session.create_dataframe(
        [Row(REGION=r, ADJUSTMENT=int(adjustments.get(r, 0))) for r in regions]
    )

    expanded = (
        wd.join(supply, on="MONTH_NUMBER", how="left")
        .join(adj_df, on="REGION", how="left")
        .with_column(
            "ADJUSTMENT",
            when(col("ADJUSTMENT").is_null(), lit(0)).otherwise(col("ADJUSTMENT")),
        )
    )

    # Compute baseline + scenario headcount and hours
    absence_days = float(vac_days_per_month) + float(sick_days_per_month)
    prod_mult = 1 - float(pct_decrease)

    scenario = (
        expanded.with_column("BASE_HEADCOUNT", col("COUNT"))
        .with_column(
            "SCENARIO_HEADCOUNT",
            when(
                col("MONTH_START") >= lit(adjustment_start_date),
                col("COUNT") + col("ADJUSTMENT"),
            ).otherwise(col("COUNT")),
        )
        .with_column("ABSENCE_DAYS_PER_FTE", lit(absence_days))
        .with_column(
            "NET_BUSINESS_DAYS",
            greatest(lit(0), col("BUSINESS_DAYS") - col("ABSENCE_DAYS_PER_FTE")),
        )
        .with_column(
            "BASE_GROSS_SUPPLY_HOURS",
            col("BASE_HEADCOUNT") * col("NET_BUSINESS_DAYS") * lit(8),
        )
        .with_column(
            "SCENARIO_GROSS_SUPPLY_HOURS",
            col("SCENARIO_HEADCOUNT") * col("NET_BUSINESS_DAYS") * lit(8),
        )
        .with_column("BASE_NET_SUPPLY_HOURS", col("BASE_GROSS_SUPPLY_HOURS") * lit(prod_mult))
        .with_column("SCENARIO_NET_SUPPLY_HOURS", col("SCENARIO_GROSS_SUPPLY_HOURS") * lit(prod_mult))
    )

    # Demand weights by project, month_number, and region (region column aliased to REGION)
    weights = (
        get_demand_weight()
        .select(
            col("CCRID"),
            col("SERVICE_REGION_ST").alias("REGION"),
            col("MONTH_NUMBER"),
            col("ALLOCATION"),
        )
    )

    # Expand to project level by joining weights on month_number + region
    scenario_alloc = (
        scenario.join(weights, on=["MONTH_NUMBER", "REGION"], how="inner")
        .with_column("BASE_PROJECT_SUPPLY_HOURS", col("BASE_NET_SUPPLY_HOURS") * col("ALLOCATION"))
        .with_column("SCENARIO_PROJECT_SUPPLY_HOURS", col("SCENARIO_NET_SUPPLY_HOURS") * col("ALLOCATION"))
    )

    # Project demand by CCRID and month_number
    demand = (
        get_demand()
        .select(
            col("CCRID"),
            col("PROJECT_NAME"),
            col("MONTH_NUMBER"),
            col("HOURS").alias("DEMAND_HOURS"),
        )
    )

    final_df = (
        scenario_alloc.join(demand, on=["CCRID", "MONTH_NUMBER"], how="left")
        .with_column(
            "DEMAND_HOURS",
            when(col("DEMAND_HOURS").is_null(), lit(0)).otherwise(col("DEMAND_HOURS")),
        )
        .with_column("BASE_GAP_HOURS", col("BASE_PROJECT_SUPPLY_HOURS") - col("DEMAND_HOURS"))
        .with_column("SCENARIO_GAP_HOURS", col("SCENARIO_PROJECT_SUPPLY_HOURS") - col("DEMAND_HOURS"))
        .with_column("SUPPLY_DELTA_HOURS", col("SCENARIO_PROJECT_SUPPLY_HOURS") - col("BASE_PROJECT_SUPPLY_HOURS"))
        .select(
            col("CCRID"),
            col("PROJECT_NAME"),
            col("REGION"),
            col("MONTH_START").alias("DATE"),
            sround(col("BASE_PROJECT_SUPPLY_HOURS"), 1).alias("BASE_SUPPLY"),
            sround(col("SCENARIO_PROJECT_SUPPLY_HOURS"), 1).alias("SCENARIO_SUPPLY"),
            sround(col("SUPPLY_DELTA_HOURS"), 1).alias("SUPPLY_DELTA"),
            sround(col("DEMAND_HOURS"), 1).alias("DEMAND"),
            sround(col("BASE_GAP_HOURS"), 1).alias("BASE_GAP"),
            sround(col("SCENARIO_GAP_HOURS"), 1).alias("SCENARIO_GAP"),
        )
        .order_by(col("DATE"), col("REGION"), col("CCRID"))
    )

    return final_df