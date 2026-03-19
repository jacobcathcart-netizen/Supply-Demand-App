import pandas as pd

from data.snowflake import (
    get_supply,
    get_working_days,
    get_demand_weight,
    get_demand,
)


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
    supply = get_supply().copy()
    supply = supply[supply["REGION"].isin(regions)].copy()

    wd = get_working_days(start_date, end_date).copy()
    wd["MONTH_START"] = pd.to_datetime(wd["MONTH_START"])
    wd["MONTH_NUMBER"] = wd["MONTH_START"].dt.month
    wd = wd[["MONTH_START", "MONTH_NUMBER", "BUSINESS_DAYS"]].copy()

    adj_df = pd.DataFrame(
        {
            "REGION": regions,
            "ADJUSTMENT": [int(adjustments.get(region, 0)) for region in regions],
        }
    )

    expanded = wd.merge(supply, on="MONTH_NUMBER", how="left")
    expanded = expanded.merge(adj_df, on="REGION", how="left")
    expanded["ADJUSTMENT"] = expanded["ADJUSTMENT"].fillna(0)

    absence_days = float(vac_days_per_month) + float(sick_days_per_month)
    prod_mult = 1 - float(pct_decrease)

    adjustment_start_ts = pd.to_datetime(adjustment_start_date)

    expanded["BASE_HEADCOUNT"] = expanded["COUNT"]
    expanded["SCENARIO_HEADCOUNT"] = expanded["COUNT"]
    expanded.loc[
        expanded["MONTH_START"] >= adjustment_start_ts,
        "SCENARIO_HEADCOUNT",
    ] = expanded["COUNT"] + expanded["ADJUSTMENT"]

    expanded["ABSENCE_DAYS_PER_FTE"] = absence_days
    expanded["NET_BUSINESS_DAYS"] = (
        expanded["BUSINESS_DAYS"] - expanded["ABSENCE_DAYS_PER_FTE"]
    ).clip(lower=0)

    expanded["BASE_GROSS_SUPPLY_HOURS"] = (
        expanded["BASE_HEADCOUNT"] * expanded["NET_BUSINESS_DAYS"] * 8
    )
    expanded["SCENARIO_GROSS_SUPPLY_HOURS"] = (
        expanded["SCENARIO_HEADCOUNT"] * expanded["NET_BUSINESS_DAYS"] * 8
    )
    expanded["BASE_NET_SUPPLY_HOURS"] = expanded["BASE_GROSS_SUPPLY_HOURS"] * prod_mult
    expanded["SCENARIO_NET_SUPPLY_HOURS"] = (
        expanded["SCENARIO_GROSS_SUPPLY_HOURS"] * prod_mult
    )

    weights = get_demand_weight().copy()
    weights = weights.rename(columns={"SERVICE_REGION_ST": "REGION"})
    weights = weights[["CCRID", "REGION", "MONTH_NUMBER", "ALLOCATION"]].copy()

    scenario_alloc = expanded.merge(
        weights,
        on=["MONTH_NUMBER", "REGION"],
        how="inner",
    )

    scenario_alloc["BASE_PROJECT_SUPPLY_HOURS"] = (
        scenario_alloc["BASE_NET_SUPPLY_HOURS"] * scenario_alloc["ALLOCATION"]
    )
    scenario_alloc["SCENARIO_PROJECT_SUPPLY_HOURS"] = (
        scenario_alloc["SCENARIO_NET_SUPPLY_HOURS"] * scenario_alloc["ALLOCATION"]
    )

    demand = get_demand().copy()
    demand = demand.rename(columns={"HOURS": "DEMAND_HOURS"})
    demand = demand[["CCRID", "PROJECT_NAME", "MONTH_NUMBER", "DEMAND_HOURS"]].copy()

    final_df = scenario_alloc.merge(
        demand,
        on=["CCRID", "MONTH_NUMBER"],
        how="left",
    )

    final_df["DEMAND_HOURS"] = final_df["DEMAND_HOURS"].fillna(0)
    final_df["BASE_GAP_HOURS"] = (
        final_df["BASE_PROJECT_SUPPLY_HOURS"] - final_df["DEMAND_HOURS"]
    )
    final_df["SCENARIO_GAP_HOURS"] = (
        final_df["SCENARIO_PROJECT_SUPPLY_HOURS"] - final_df["DEMAND_HOURS"]
    )
    final_df["SUPPLY_DELTA_HOURS"] = (
        final_df["SCENARIO_PROJECT_SUPPLY_HOURS"]
        - final_df["BASE_PROJECT_SUPPLY_HOURS"]
    )

    final_df = final_df.rename(columns={"MONTH_START": "DATE"})

    final_df = final_df[
        [
            "CCRID",
            "PROJECT_NAME",
            "REGION",
            "DATE",
            "BASE_PROJECT_SUPPLY_HOURS",
            "SCENARIO_PROJECT_SUPPLY_HOURS",
            "SUPPLY_DELTA_HOURS",
            "DEMAND_HOURS",
            "BASE_GAP_HOURS",
            "SCENARIO_GAP_HOURS",
        ]
    ].copy()

    final_df = final_df.rename(
        columns={
            "BASE_PROJECT_SUPPLY_HOURS": "BASE_SUPPLY",
            "SCENARIO_PROJECT_SUPPLY_HOURS": "SCENARIO_SUPPLY",
            "SUPPLY_DELTA_HOURS": "SUPPLY_DELTA",
            "DEMAND_HOURS": "DEMAND",
            "BASE_GAP_HOURS": "BASE_GAP",
            "SCENARIO_GAP_HOURS": "SCENARIO_GAP",
        }
    )

    numeric_cols = [
        "BASE_SUPPLY",
        "SCENARIO_SUPPLY",
        "SUPPLY_DELTA",
        "DEMAND",
        "BASE_GAP",
        "SCENARIO_GAP",
    ]
    final_df[numeric_cols] = final_df[numeric_cols].round(1)

    final_df = final_df.sort_values(["DATE", "REGION", "CCRID"]).reset_index(drop=True)

    return final_df